#
# Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#


import collections
import datetime
import math
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QMargins
from PyQt5.QtCore import QRegExp
from PyQt5.QtCore import pyqtSignal

from PyQt5.QtWidgets import QButtonGroup
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtWidgets import QDateTimeEdit
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QRadioButton
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QTimeEdit
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

import gripe
import gripe.db
import grumble.model
import grumble.property

logger = gripe.get_logger(__name__)

class DisplayConverter(object):
    _delegate = None
    _suffix = None

    def __init__(self, delegate = None, **config):
        self._delegate = delegate
        self._suffix = config.get("suffix")
        self._label = config.get("label",
                        config.get("verbose_name"))

    def setProperty(self, property):
        self._property = property
        if not self._label:
            self._label = property.verbose_name
        if self._delegate:
            self._delegate.setProperty(property)

    def label(self, instance):
        return self._delegate.label(instance) \
            if self._delegate \
            else self._label

    def suffix(self, instance):
        return self._delegate.suffix(instance) \
            if self._delegate \
            else self._suffix

    def to_display(self, value, instance):
        return self._delegate.to_display(value, instance) \
            if self._delegate \
            else value

    def from_display(self, displayvalue, instance):
        return self._delegate.from_display(displayvalue, instance) \
            if self._delegate \
            else displayvalue


class WidgetBridgeFactory(type):
    _widgetbridgetypes = { }

    def __new__(cls, name, bases, dct):
        ret = type.__new__(cls, name, bases, dct)
        if hasattr(ret, "_grumbletypes"):
            for datatype in ret._grumbletypes:
                WidgetBridgeFactory._widgetbridgetypes[datatype] = ret
        return ret

    @classmethod
    def get(cls, parent, kind, propname, **kwargs):
        property = getattr(kind, propname)

        # Allow for custom bridges. Note that if you configure
        # a custom bridge, you have to deal with read-onliness and
        # multiple-choiciness yourself.
        bridge = kwargs.get("bridge", property.config.get("bridge"))
        if bridge:
            if not isinstance(bridge, WidgetBridgeFactory):
                bridge = gripe.resolve(bridge)
            return bridge(parent, kind, propname, **kwargs)

        if "readonly" in kwargs or \
                property.is_key or \
                property.readonly:
            return Label(parent, kind, propname, **kwargs)
        if property.config.get("choices") or kwargs.get("choices"):
            if kwargs.get("style", "combo").lower() == "combo":
                return ComboBox(parent, kind, propname, **kwargs)
            elif kwargs["style"].lower() == "radio":
                return RadioButtons(parent, kind, propname, **kwargs)
            # else we fall down to default processing...
        bridge = cls._widgetbridgetypes.get(property.__class__)
        assert bridge, "I'm not ready to handle properties of type '%s'" % type(property)
        return bridge(parent, kind, propname, **kwargs)


class WidgetBridge(object):
    __metaclass__ = WidgetBridgeFactory

    def __init__(self, parent, kind, path, **kwargs):
        self.parent = parent
        self.name = path
        propname = path.split(".")[-1]
        self.property = getattr(kind, propname)
        self.config = dict(self.property.config)
        self.config.update(kwargs)
        self.converter = self.config.get("displayconverter")
        if not self.converter:
            self.converter = DisplayConverter(
                                 suffix = self.config.get("suffix"),
                                 label = self.config.get("verbose_name", propname)
                             )
        if hasattr(self, "getDisplayConverter"):
            self.converter = self.getDisplayConverter(self.converter)
        self.converter.setProperty(self.property)
        self.choices = self.config.get("choices")
        self.hasLabel = self.config.get("has_label", True)
        self.assigned = None
        self.container = None
        self.suffix = None
        self.label = None
        self.widget = self.create()
        if not self.container:
            self.container = self.widget

    def getWidgetType(self):
        return self._qttype if hasattr(self, "_qttype") else None

    def create(self):
        self.widget = self._createWidget()
        if hasattr(self, "customize") and callable(self.customize):
            self.customize(self.widget)
        if self.converter.suffix(None):
            self.container = QWidget(self.parent)
            self.suffix = QLabel("", self.parent)
            hbox = QHBoxLayout(self.container)
            hbox.addWidget(self.widget)
            hbox.addWidget(self.suffix)
            hbox.addStretch(1)
            hbox.setContentsMargins(QMargins(0, 0, 0, 0))
        if self.converter.label(None) and self.hasLabel:
            self.label = QLabel(self.parent)
            self.label.setBuddy(self.widget)
        return self.widget

    def _createWidget(self):
        return self.getWidgetType()(parent = self.parent)

    def setValue(self, instance):
        if self.label:
            self.label.setText(str(self.converter.label(instance)) + ":")
        if self.suffix:
            self.suffix.setText(str(self.converter.suffix(instance)))
        value = getattr(instance, self.property.name)
        displayvalue = self.converter.to_display(value, instance)
        self.assigned = displayvalue
        self.apply(displayvalue)

    def apply(self, value):
        self.widget.setText(str(value))

    def getValue(self, instance):
        displayvalue = self.retrieve()
        value = self.converter.from_display(displayvalue, instance)
        return value

    def retrieve(self):
        return self._pytype(self.widget.text())

    def isModified(self):
        return self.assigned != self.retrieve()


class Label(WidgetBridge):
    _qttype = QLabel

    def apply(self, value):
        fmt = self.config.get("format")
        if fmt:
            fmt = "{:" + fmt + "}"
            value = fmt.format(value) if value is not None else ''
        self.widget.setText(str(value))

    def retrieve(self):
        pass

    def isModified(self):
        return False


class Image(Label):
    def customize(self, widget):
        self.height = int(self.config.get("height", 0))
        self.width = int(self.config.get("width", 0))
        if self.height and not self.width:
            self.width = self.height
        if self.width and not self.height:
            self.height = self.width


    def apply(self, value):
        if isinstance(value, basestring):
            value = QPixmap(value)
        assert isinstance(value, QPixmap), "Image bridge must be assigned a pixmap"
        if self.width and self.height:
            value = value.scaled(self.width, self.height)
        self.widget.setPixmap(value)


class TimeDeltaLabel(Label, DisplayConverter):
    _grumbletypes = [ grumble.property.TimeDeltaProperty ]

    def getDisplayConverter(self):
        return self

    def to_display(self, value, instance):
        h = int(math.floor(value.seconds / 3600))
        r = value.seconds - (h * 3600)
        m = int(math.floor(r / 60))
        s = r % 60
        if h > 0:
            return "%dh %02d'%02d\"" % (h, m, s)
        else:
            return "%d'%02d\"" % (m, s)


class LineEdit(WidgetBridge):
    _grumbletypes = [
        grumble.property.TextProperty,
        grumble.property.StringProperty,
        grumble.property.LinkProperty
    ]
    _qttype = QLineEdit
    _pytype = str

    def customize(self, widget):
        regexp = self.config.get("regexp")
        validator = None
        if regexp:
            validator = QRegExpValidator(QRegExp(regexp), self.parent)
            if "casesensitive" in self.config:
                cs = bool(self.config("casesensitive"))
                validator.setCaseSensitivity(
                    Qt.CaseSensitive if cs else Qt.CaseInsensitive)
        maxlength = int(self.config.get("maxlength", 0))
        if maxlength > 0:
            widget.setMaxLength(maxlength)
            fm = widget.fontMetrics()
            widget.setMaximumWidth(maxlength * fm.maxWidth() + 11)
        if hasattr(self, "_createValidator") and \
                callable(self._createValidator):
            validator = self._createValidator()
        if validator:
            widget.setValidator(validator)


class PasswordEdit(LineEdit):
    _grumbletypes = [grumble.property.PasswordProperty]

    def customize(self, widget):
        super(PasswordEdit, self).customize(widget)
        widget.setEchoMode(QLineEdit.Password)


class IntEdit(LineEdit):
    _grumbletypes = [grumble.property.IntegerProperty]
    _pytype = int

    def customize(self, widget):
        super(IntEdit, self).customize(widget)
        fm = widget.fontMetrics()
        sz = None
        if "min" in self.config:
            sz = fm.width(str(self.config["min"]))
        if "max" in self.config:
            sz = max(sz, fm.width(str(self.config["max"])))
        if not sz:
            sz = fm.width("-50000")
        widget.setMaximumWidth(sz + 20)

    def _createValidator(self):
        validator = QIntValidator(self.parent)
        if "min" in self.config:
            validator.setBottom(int(self.config["min"]))
        if "max" in self.config:
            validator.setTop(int(self.config["max"]))
        return validator


class FloatEdit(LineEdit):
    _grumbletypes = [grumble.property.FloatProperty]
    _pytype = float

    def customize(self, widget):
        super(FloatEdit, self).customize(widget)
        fm = widget.fontMetrics()
        sz = None
        if "decimals" in self.config:
            decimals = int(self.config["decimals"])
        else:
            decimals = 4
        decwidth = fm.width(".") + decimals * fm.width("0")
        if "min" in self.config:
            sz = fm.width(str(self.config["min"]))
        if "max" in self.config:
            sz = max(sz, fm.width(str(self.config["max"])))
        if not sz:
            sz = fm.width("1000000")
        widget.setMaximumWidth(sz + decwidth + 20)

    def _createValidator(self):
        validator = QDoubleValidator(self.parent)
        if "min" in self.config:
            validator.setBottom(int(self.config["min"]))
        if "max" in self.config:
            validator.setTop(int(self.config["max"]))
        if "decimals" in self.config:
            validator.setDecimals(int(self.config["decimals"]))
        return validator


class DateEdit(WidgetBridge):
    _grumbletypes = [grumble.property.DateProperty]
    _qttype = QDateEdit
    _pytype = datetime.date

    def customize(self, widget):
        widget.setDisplayFormat("MMMM d, yyyy")
        widget.setCalendarPopup(True)
        fm = widget.fontMetrics()
        widget.setMaximumWidth(fm.width("September 29, 2000") + 31)  # FIXME
        self.assigned = None

    def apply(self, value):
        self.widget.setDate(value if value else datetime.date.today())

    def retrieve(self):
        return self.widget.date().toPyDate()


class DateTimeEdit(WidgetBridge):
    _grumbletypes = [grumble.property.DateTimeProperty]
    _qttype = QDateTimeEdit
    _pytype = datetime.datetime

    def customize(self, widget):
        widget.setDisplayFormat("MMMM d, yyyy h:mm:ss ap")
        widget.setCalendarPopup(True)
        fm = widget.fontMetrics()
        widget.setMaximumWidth(fm.width("September 29, 2000 12:00:00 pm") + 31)  # FIXME
        self.assigned = None

    def apply(self, value):
        self.widget.setDateTime(value)

    def retrieve(self):
        return self.widget.dateTime().toPyDateTime()


class TimeEdit(WidgetBridge):
    _grumbletypes = [grumble.property.TimeProperty]
    _qttype = QTimeEdit
    _pytype = datetime.time

    def customize(self, widget):
        widget.setDisplayFormat("h:mm:ss ap")
        fm = widget.fontMetrics()
        widget.setMaximumWidth(fm.width("12:00:00 pm") + 31)  # FIXME
        self.assigned = None

    def apply(self, value):
        self.widget.setTime(value)

    def retrieve(self):
        return self.widget.time().toPython()


class CheckBox(WidgetBridge):
    _grumbletypes = [grumble.property.BooleanProperty]
    _qttype = QCheckBox
    _pytype = bool

    def customize(self, widget):
        widget.setText(self.label)
        self.hasLabel = False

    def apply(self, value):
        self.widget.setChecked(value)

    def retrieve(self):
        return self.widget.isChecked()


class Choices():
    def _initialize_choices(self):
        if not hasattr(self, "_choices"):
            self._choices = collections.OrderedDict()
            if hasattr(self, "choices") and self.choices:
                if hasattr(self, "required") and not self.required:
                    self._choices[None] = ""
                for c in self.choices:
                    # self.choices can be a listy thing or a dicty thing
                    # we try to access it as a dicty thing first, and if
                    # that bombs we assume it's a listy thing.
                    try:
                        self._choices[c] = self.choices[c]
                    except:
                        self._choices[c] = c

    def choicesdict(self):
        self._initialize_choices()
        return self._choices

    def index(self, value):
        self._initialize_choices();
        count = 0;
        for c in self._choices:
            if c == value:
                return count
            count += 1
        return -1


    def at(self, index):
        self._initialize_choices();
        count = 0;
        for c in self._choices:
            if count == index:
                return c
            count += 1
        return None


class ComboBox(WidgetBridge, Choices):
    _qttype = QComboBox

    def __init__(self, parent, kind, propname, **kwargs):
        super(ComboBox, self).__init__(parent, kind, propname, **kwargs)

    def customize(self, widget):
        assert self.choices, "ComboBox: Cannot build widget bridge without choices"
        self.required = "required" in self.config
        for (key, text) in self.choicesdict().items():
            widget.addItem(text, key)

    def apply(self, value):
        self.assigned = value
        self.widget.setCurrentIndex(self.index(value))

    def retrieve(self):
        return self.at(self.widget.currentIndex())


class RadioButtons(WidgetBridge, Choices):
    _qttype = QGroupBox

    def customize(self, widget):
        assert self.choices, "RadioButtons: Cannot build widget bridge without choices"
        # We give the GroupBox a container so we can add stretch at the end.
        self.container = QWidget(self.parent)
        hbox = QHBoxLayout(self.container)
        self.buttongroup = QButtonGroup(self.parent)
        if "direction" in self.config and \
                self.config["direction"].lower() == "vertical":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        ix = 1
        for text in self.choicesdict().values():
            rb = QRadioButton(text, self.parent)
            box.addWidget(rb)
            self.buttongroup.addButton(rb, ix)
            ix += 1
        widget.setLayout(box)
        hbox.addWidget(widget)
        hbox.addStretch(1)
        hbox.setContentsMargins(QMargins(0, 0, 0, 0))

    def apply(self, value):
        for b in self.buttongroup.buttons():
            b.setChecked(False)
        b = self.buttongroup.button(self.index(value) + 1)
        if b:
            b.setChecked(True)

    def retrieve(self):
        ix = self.buttongroup.checkedId()
        return self.at(ix - 1) if ix > 0 else None


class PropertyFormLayout(QGridLayout):
    def __init__(self, parent = None):
        super(PropertyFormLayout, self).__init__(parent)
        self._properties = {}
        self.sublayouts = []

    def addProperty(self, parent, kind, path, row, col, *args, **kwargs):
        pnames = path.split(".")
        pname = pnames[-1]
        bridge = WidgetBridgeFactory.get(parent, kind, pname, **kwargs)
        self._properties[path] = bridge
        rowspan = int(kwargs.get("rowspan", 1))
        if bridge.label:
            labelspan = int(kwargs.get("labelspan", 1))
            self.addWidget(bridge.label, row, col,
                           rowspan, labelspan)
            col += labelspan
        colspan = int(kwargs.get("colspan", 1))
        self.addWidget(bridge.container, row, col, rowspan, colspan)

    def addSubLayout(self, layout):
        self.addSubLayouts(layout)

    def addSubLayouts(self, *layouts):
        for layout in layouts:
            self.sublayouts.append(layout)

    def addLayout(self, layout, *args):
        if isinstance(layout, PropertyFormLayout):
            self.sublayouts.append(layout)
        super(PropertyFormLayout, self).addLayout(layout, *args)

    def _setValues(self, instance):
        for (p, bridge) in self._properties.items():
            path = p.split(".")
            i = reduce(lambda i, n : getattr(i, n),
                       path[:-1],
                       instance)
            # logger.debug("Set bridge widget value: %s(%s/%s), %s", bridge.name, bridge.__class__.__name__,
            #         bridge.widget.__class__.__name__, i)
            bridge.setValue(i)
        for s in self.sublayouts:
            s._setValues(instance)

    def apply(self, instance):
        with gripe.db.Tx.begin():
            self._setValues(instance)

    def _getValues(self, instance):
        instances = set()
        for (p, bridge) in filter(lambda (p, b): b.isModified(), self._properties.items()):
            path = p.split(".")
            i = reduce(lambda i, n : getattr(i, n),
                       path[:-1],
                       instance)
            v = bridge.getValue(i)
            setattr(i, path[-1], v)
            instances.add(i)
            bridge.setValue(i)
        for s in self.sublayouts:
            instances |= s._getValues(instance)
        return instances

    def retrieve(self, instance):
        with gripe.db.Tx.begin():
            instances = self._getValues(instance)
            for i in instances:
                i.put()


class FormPage(QWidget):
    statusMessage = pyqtSignal(str)

    def __init__(self, parent):
        super(FormPage, self).__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        formframe = QGroupBox(self)
        self.vbox = QVBoxLayout(formframe)
        self.form = PropertyFormLayout()
        self.vbox.addLayout(self.form)
        self.vbox.addStretch(1)
        self._has_stretch = True
        layout.addWidget(formframe)

    def _removeStretch(self):
        if self._has_stretch:
            self.vbox.removeItem(self.vbox.itemAt(self.vbox.count() - 1))
            self._has_stretch = False;

    def addStretch(self):
        if not self._has_stretch:
            self.vbox.addStretch(1)
            self._has_stretch = True

    def addProperty(self, kind, path, row, col, *args, **kwargs):
        self.form.addProperty(self, kind, path, row, col, *args, **kwargs)

    def addWidget(self, widget, *args):
        self._removeStretch()
        self.form.addWidget(widget, *args)

    def addLayout(self, sublayout, *args):
        self._removeStretch()
        self.form.addLayout(sublayout, *args)

    def status_message(self, msg, *args):
        self.statusMessage.emit(msg.format(*args))

class FormButtons(object):
    NoButtons = 0
    SaveButton = 1
    ResetButton = 2
    EditButtons = 3
    DeleteButton = 4
    AllButtons = 7

class FormWidget(FormPage):
    instanceAssigned = pyqtSignal(str)
    instanceDeleted = pyqtSignal(str)
    instanceSaved = pyqtSignal(str)
    exception = pyqtSignal(str)

    def __init__(self, parent = None, buttons = FormButtons.EditButtons):
        super(FormWidget, self).__init__(parent)
        self.buildButtonBox(buttons)
        self.tabs = None
        self._tabs = {}

    def buildButtonBox(self, buttons):
        buttonWidget = QGroupBox()
        self.buttonbox = QHBoxLayout(buttonWidget)
        if buttons & FormButtons.DeleteButton:
            self.deletebutton = QPushButton("Delete", self)
            self.deletebutton.clicked.connect(self.deleteInstance)
            self.buttonbox.addWidget(self.deletebutton)
        self.buttonbox.addStretch(1)
        if buttons & FormButtons.ResetButton:
            self.resetbutton = QPushButton("Reset", self)
            self.resetbutton.clicked.connect(self.setInstance)
            self.buttonbox.addWidget(self.resetbutton)
        if buttons & FormButtons.SaveButton:
            self.savebutton = QPushButton("Save", self)
            self.savebutton.clicked.connect(self.save)
            self.buttonbox.addWidget(self.savebutton)
        self.layout().addWidget(buttonWidget)

    def addWidgetToButtonBox(self, widget, *args):
        self.buttonbox.insertWidget(0, widget, *args)

    def addTab(self, widget, title):
        if self.tabs is None:
            self.tabs = QTabWidget(self)
            self.tabs.currentChanged[int].connect(self.tabChanged)

            # Remove stretch at the bottom:
            self._removeStretch()
            self.vbox.addWidget(self.tabs, 1)
        if isinstance(widget, FormPage):
            self.form.addSubLayout(widget.form)
        self.tabs.addTab(widget, title)
        self._tabs[title] = widget
        return widget

    def count(self):
        return self.tabs and self.tabs.count()

    def setTab(self, tab):
        if self.tabs and tab <= self.tabs.count():
            self.tabs.setCurrentIndex(tab)

    def tabChanged(self, ix):
        w = self.tabs.currentWidget()
        if hasattr(w, "selected"):
            w.selected()

    def save(self):
        try:
            self.form.retrieve(self.instance())
            if hasattr(self, "retrieve") and callable(self.retrieve):
                self.retrieve(self.instance())
            self.instanceSaved.emit(str(self.instance.key()))
            self.statusMessage.emit("Saved")
        except:
            self.exception.emit("Save failed...")
        self.setInstance()

    def instance(self):
        return self._instance

    def setInstance(self, instance = None):
        if instance:
            self._instance = instance
        self.form.apply(self.instance())
        if hasattr(self, "assign") and callable(self.assign):
            self.assign(self.instance())
        self.instanceAssigned.emit(str(self.instance().key()))

    def confirmDelete(self):
        return QMessageBox.warning(self, "Are you sure?",
                                   "Are you sure you want to delete this?",
                                    QMessageBox.Cancel | QMessageBox.Ok,
                                    QMessageBox.Cancel) == QMessageBox.Ok

    def onDelete(self):
        try:
            with gripe.db.Tx.begin():
                key = str(self.instance().key())
                if grumble.model.delete(self.instance()):
                    self.instanceDeleted.emit(key)
        except:
            traceback.print_exc()
            self.exception.emit("Delete failed...")

    def deleteInstance(self):
        if self.instance() and self.confirmDelete():
            self.onDelete()

