'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import Qt
from PySide.QtCore import QCoreApplication
from PySide.QtCore import QRegExp

from PySide.QtGui import QButtonGroup
from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QPushButton
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import grizzle
import grumble.qt.bridge
import sweattrails.userprofile

logger = gripe.get_logger("qt")

class SettingsPage(QWidget):
    def __init__(self, parent = None):
        super(SettingsPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.fields = {}
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.form = grumble.qt.bridge.PropertyFormLayout()
        layout.addLayout(self.form)
        self.form.addProperty(self, grizzle.User, "email")
        self.form.addProperty(self, grizzle.User, "display_name")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.dob")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.gender",
                              style = "radio")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.height",
                              min = 100, max = 240)
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.units",
                              style = "radio")

    def setValues(self):
        self.form.setValues(QCoreApplication.instance().user)


class ZonesPage(QWidget):
    def __init__(self, parent = None):
        super(ZonesPage, self).__init__(parent)
        self.setMinimumSize(800, 600)

    def setValues(self):
        pass


class ProfileTab(QWidget):
    def __init__(self, parent = None):
        super(ProfileTab, self).__init__(parent)
        layout = QHBoxLayout()
        leftpane = QVBoxLayout()

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
        gb.setMinimumWidth(200)
        gb.setLayout(gb_layout)
        leftpane.addWidget(gb)
        leftpane.addStretch(1)
        layout.addLayout(leftpane)

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
