'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QPushButton
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import grizzle
import grumble.qt.bridge
import sweattrails.qt.stackedpage
import sweattrails.userprofile

logger = gripe.get_logger("qt")

class SettingsPage(QWidget):
    def __init__(self, parent = None):
        super(SettingsPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.fields = {}
        layout = QVBoxLayout(self)
        formframe = QGroupBox()
        vbox = QVBoxLayout(formframe)
        self.form = grumble.qt.bridge.PropertyFormLayout()
        self.form.addProperty(self, grizzle.User, "email")
        self.form.addProperty(self, grizzle.User, "display_name")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.dob")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.gender",
                              style = "radio")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.height",
                              min = 100, max = 240, suffix = "cm")
        self.form.addProperty(self, sweattrails.userprofile.UserProfile,
                              "_userprofile.units",
                              style = "radio")
        vbox.addLayout(self.form)
        vbox.addStretch(1)
        layout.addWidget(formframe)
        buttons = QGroupBox()
        hbox = QHBoxLayout(buttons)
        hbox.addStretch(1)
        self.resetbutton = QPushButton("Reset", self)
        self.resetbutton.clicked.connect(self.activate)
        hbox.addWidget(self.resetbutton)
        self.savebutton = QPushButton("Save", self)
        self.savebutton.clicked.connect(self.save)
        hbox.addWidget(self.savebutton)
        layout.addWidget(buttons)

    def activate(self):
        self.form.setValues(QCoreApplication.instance().user)
        
    def save(self):
        try:
            self.form.getValues(QCoreApplication.instance().user)
            QCoreApplication.instance().mainwindow.log("Saved")
        except:
            QCoreApplication.instance().mainwindow.log("Save failed...")
            raise
        self.activate()


class ZonesPage(QWidget):
    def __init__(self, parent = None):
        super(ZonesPage, self).__init__(parent)
        self.setMinimumSize(800, 600)

    def activate(self):
        pass


class ProfileTab(sweattrails.qt.stackedpage.StackedPage):
    def __init__(self, parent = None):
        super(ProfileTab, self).__init__(parent)
        self.addPage("Settings", SettingsPage())
        self.addPage("Zones and FTP", ZonesPage())
