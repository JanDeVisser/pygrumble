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

class SettingsPage(grumble.qt.bridge.FormWidget):
    def __init__(self, parent = None):
        super(SettingsPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.addProperty(grizzle.User, "email")
        self.addProperty(grizzle.User, "display_name")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.dob")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.gender",
                         style = "radio")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.height",
                         min = 100, max = 240, suffix = "cm")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.units",
                         style = "radio")
        self.logmessage.connect(QCoreApplication.instance().log)

    def activate(self):
        self.setInstance(QCoreApplication.instance().user)


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
