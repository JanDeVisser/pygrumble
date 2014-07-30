'''
Created on Jul 29, 2014

@author: jan
'''

from PySide.QtCore import Qt
from PySide.QtCore import QRegExp

from PySide.QtGui import QButtonGroup
from PySide.QtGui import QCheckBox
from PySide.QtGui import QComboBox
from PySide.QtGui import QDateEdit
from PySide.QtGui import QDateTimeEdit
from PySide.QtGui import QDoubleValidator
from PySide.QtGui import QFormLayout
from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QIntValidator
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QRadioButton
from PySide.QtGui import QRegExpValidator
from PySide.QtGui import QTimeEdit
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import gripe.db
import grumble.property

logger = gripe.get_logger("qt")

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

    def __init__(self, parent, kind, propname, **kwargs):
        self.parent = parent
        self.name = propname
        self.property = getattr(kind, propname)
        self.label = kwargs.get("label", self.property.verbose_name)
        self.config = dict(self.property.config)
        self.config.update(kwargs)
        self.choices = self.config.get("choices")
        self.hasOwnLabel = False
        self.widget = self.create()

    def getWidgetType(self):
        return self._qttype if hasattr(self, "_qttype") else None

    def create(self):
        self.widget = self._createWidget()
        logger.debug("WidgetBridge: Created Qt Widget of type %s", type(self.widget))
        return self.widget

    def _createWidget(self):
        ret = self.getWidgetType()(parent = self.parent)
        if hasattr(self, "customize") and callable(self.customize):
            self.customize(ret)
        return ret

    def setValue(self, value):
        self.widget.setText(str(value))

    def getValue(self):
        return self.widget.text()


class Label(WidgetBridge):
    _qttype = QLabel

    def setValue(self, value):
        fmt = self.config.get("format")
        if fmt:
            fmt = "{:" + fmt + "}"
            value = fmt.format(value) if value is not None else ''
        self.widget.setText(str(value))

    def getValue(self):
        pass


class LineEdit(WidgetBridge):
    _grumbletypes = [
        grumble.property.TextProperty,
        grumble.property.StringProperty,
        grumble.property.LinkProperty
    ]
    _qttype = QLineEdit

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

    def setValue(self, value):
        self.widget.setDate(value)

    def getValue(self):
        return self.widget.date()


class DateTimeEdit(WidgetBridge):
    _grumbletypes = [grumble.property.DateTimeProperty]
    _qttype = QDateTimeEdit

    def setValue(self, value):
        self.widget.setDateTime(value)

    def getValue(self):
        return self.widget.dateTime()


class TimeEdit(WidgetBridge):
    _grumbletypes = [grumble.property.TimeProperty]
    _qttype = QTimeEdit

    def setValue(self, value):
        self.widget.setTime(value)

    def getValue(self):
        return self.widget.time()


class CheckBox(WidgetBridge):
    _grumbletypes = [grumble.property.BooleanProperty]
    _qttype = QCheckBox

    def _createWidget(self):
        ret = super(CheckBox, self)._createWidget()
        ret.setText(self.label)
        self.hasOwnLabel = True
        return ret

    def setValue(self, value):
        self.widget.setChecked(value)

    def getValue(self):
        return self.widget.isChecked()


class ComboBox(WidgetBridge):
    _qttype = QComboBox

    def __init__(self, parent, kind, propname, **kwargs):
        super(ComboBox, self).__init__(parent, kind, propname, **kwargs)

    def _createWidget(self):
        assert self.choices, "ComboBox: Cannot build widget bridge without choices"
        ret = super(ComboBox, self)._createWidget()
        self.required = "required" in self.config
        if not self.required:
            ret.addItem("")
        ret.addItems(self.choices)
        return ret

    def setValue(self, value):
        if not self.required:
            ix = 0 if not value else self.choices.index(value) + 1
        else:
            ix = self.choices.index(value)
        self.widget.setCurrentIndex(ix)

    def getValue(self):
        ix = self.widget.currentIndex()
        if not self.required:
            ret = None if ix == 0 else self.choices[ix - 1]
        else:
            ret = self.choices[ix]
        return ret


class RadioButtons(WidgetBridge):
    def _createWidget(self):
        assert self.choices, "RadioButtons: Cannot build widget bridge without choices"
        self.buttongroup = QButtonGroup(self.parent)
        ret = QWidget(self.parent)
        hbox = QHBoxLayout()
        gb = QGroupBox(self.parent)
        if "direction" in self.config and \
                self.config["direction"].lower() == "vertical":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        if not self.property.required:
            logger.debug("RadioButtons bridge on not required property doesn't make much sense")
        for c in self.choices:
            rb = QRadioButton(c, self.parent)
            box.addWidget(rb)
            self.buttongroup.addButton(rb)
        gb.setLayout(box)
        hbox.addWidget(gb)
        hbox.addStretch(1)
        margins = hbox.contentsMargins()
        margins.setLeft(0)
        hbox.setContentsMargins(margins)
        ret.setLayout(hbox)
        return ret

    def setValue(self, value):
        for b in self.buttongroup.buttons():
            b.setChecked(b.text() == value)

    def getValue(self):
        b = self.buttongroup.checkedButton()
        return b.text()


class PropertyFormLayout(QFormLayout):
    def __init__(self, parent = None):
        super(PropertyFormLayout, self).__init__(parent)
        self._properties = {}

    def addProperty(self, parent, kind, propname, **kwargs):
        pnames = propname.split(".")
        pname = pnames[-1]
        bridge = WidgetBridgeFactory.get(parent, kind, pname, **kwargs)
        self._properties[propname] = bridge
        if bridge.hasOwnLabel:
            self.addRow(bridge.widget)
        else:
            self.addRow(bridge.label + ":", bridge.widget)

    def setValues(self, instance):
        with gripe.db.Tx.begin():
            for (p, bridge) in self._properties.items():
                bridge.setValue(reduce(lambda v, n : getattr(v, n),
                                       p.split("."),
                                       instance))

    def getValues(self, instance):
        with gripe.db.Tx.begin():
            for (p, bridge) in self._properties.items():
                v = bridge.getValue()
                path = p.split(".")
                i = reduce(lambda i, n : getattr(i, n),
                           path[:-1],
                           instance)
                setattr(i, path[-1], v)


