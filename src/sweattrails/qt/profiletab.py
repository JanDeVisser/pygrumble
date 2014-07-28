'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QButtonGroup
from PySide.QtGui import QCheckBox
from PySide.QtGui import QComboBox
from PySide.QtGui import QDateEdit
from PySide.QtGui import QDateTimeEdit
from PySide.QtGui import QTimeEdit
from PySide.QtGui import QFormLayout
from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QPushButton
from PySide.QtGui import QRadioButton
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import gripe.db
import grizzle
import grumble.qt
import sweattrails.config
import sweattrails.userprofile

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
        if "readonly" in kwargs or \
                property.is_key or \
                property.readonly:
            return Label(parent, kind, propname, **kwargs)
        if (hasattr(property, "choices") and property.choices) or \
                "choices" in kwargs:
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
        self._options = kwargs
        self.hasOwnLabel = False
        self.widget = self.create()

    def getWidgetType(self):
        return self._qttype if hasattr(self, "_qttype") else None
    
    def create(self):
        self.widget = self._createWidget()
        logger.debug("WidgetBridge: Created Qt Widget of type %s", type(self.widget))
        return self.widget
    
    def _createWidget(self):
        return self.getWidgetType()(parent = self.parent)
    
    def setValue(self, value):
        self.widget.setText(value)

    def getValue(self):
        return self.widget.text()


class Label(WidgetBridge):
    _qttype = QLabel
        
    def setValue(self, value):
        fmt = self._options.get("format")
        if fmt:
            fmt = "{:" + fmt + "}" 
            value = fmt.format(value) if value is not None else ''
        self.widget.setText(value)

    def getValue(self):
        pass
    
    
class LineEdit(WidgetBridge):
    _grumbletypes = [grumble.property.TextProperty, grumble.property.StringProperty, grumble.property.PasswordProperty]
    _qttype = QLineEdit


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

    def _createWidget(self):
        ret = super(ComboBox, self)._createWidget()
        self.choices = self._options.choices \
            if self._options.choices \
            else self.property.choices if hasattr(self.property, "choices") else None
        assert self.choices, "ComboBox bridge: Cannot build ComboBox without choices"
        self.required = "required" in self._options or \
                            not self.property.required
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
            ret = None if ix == 0 else self.choices[ix-1]
        else:
            ret = self.choices[ix]
        return ret


class RadioButtons(WidgetBridge):
    def _createWidget(self):
        self.choices = self.property.choices
        self.buttongroup = QButtonGroup(self.parent)
        ret = QGroupBox(self.parent)
        if "direction" in self._options and \
                self._options["direction"].lower() == "vertical":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        if not self.property.required:
            logger.debug("RadioButtons bridge on not required property doesn't make much sense")
        for c in self.property.choices:
            rb = QRadioButton(c, self._grumblebridge.parent)
            box.addWidget(rb)
            self.buttongroup.addButton(rb)
        ret.setLayout(box)
        return ret

    def setValue(self, value):
        for b in self.buttongroup.buttons():
            b.setChecked(b.getText() == value)

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
                bridge.setValue(reduce(lambda v,n : getattr(v,n), p.split("."), instance))

class SettingsPage(QWidget):
    def __init__(self, parent = None):
        super(SettingsPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.fields = {}
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.form = PropertyFormLayout()
        layout.addLayout(self.form)
        self.form.addProperty(self, grizzle.User, "email")
        self.form.addProperty(self, grizzle.User, "display_name")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile, "_userprofile.dob")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile, "_userprofile.gender", 
                              style = "radio")
        #self.form.addProperty(self, sweattrails.userprofile.UserProfile, "_userprofile.height") 
        self.form.addProperty(self, sweattrails.userprofile.UserProfile, "_userprofile.units", 
                              style = "radio")

    def setValues(self):
        self.form.setValues(QCoreApplication.instance().user)


class ZonesPage(QWidget):
    def __init__(self, parent=None):
        super(ZonesPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        
    def setValues(self):
        pass


class ProfileTab(QWidget):
    def __init__(self, parent = None):
        super(ProfileTab, self).__init__(parent)
        layout = QHBoxLayout()

        bg = QButtonGroup(self)
        bg.setExclusive(True)
        bg.buttonClicked[int].connect(self.switchPage)
        gb = QGroupBox()
        gb_layout = QVBoxLayout()
        settings_button = QPushButton("Settings")
        settings_button.setCheckable(True)
        settings_button.setChecked(True)
        bg.addButton(settings_button, 0)
        gb_layout.addWidget(settings_button)
        zones_button = QPushButton("Zones and FTP")
        zones_button.setCheckable(True)
        bg.addButton(zones_button, 1)
        gb_layout.addWidget(zones_button)
        gb.setLayout(gb_layout)
        layout.addWidget(gb)

        self.pages = []
        self.pages.append(SettingsPage())
        self.pages.append(ZonesPage())
        for p in self.pages:
            layout.addWidget(p)
        self.switchPage(0)
        self.setLayout(layout)

    def switchPage(self, buttonid):
        for i in range(len(self.pages)):
            self.pages[i].setVisible(buttonid == i)

    def setValues(self):
        for p in self.pages:
            p.setValues()
