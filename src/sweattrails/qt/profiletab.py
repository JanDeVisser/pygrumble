'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication
from PySide.QtGui import QWidget

import gripe
import grizzle
import grumble.qt.bridge
import sweattrails.qt.stackedpage
import sweattrails.userprofile

logger = gripe.get_logger(__name__)

class SettingsPage(grumble.qt.bridge.FormWidget):
    def __init__(self, parent = None):
        super(SettingsPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.addProperty(grizzle.User, "email", 0, 0)
        self.addProperty(grizzle.User, "display_name", 1, 0)
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.dob", 2, 0)
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.gender", 3, 0,
                         style = "radio")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.height", 4, 0,
                         min = 100, max = 240, suffix = "cm")
        self.addProperty(sweattrails.userprofile.UserProfile,
                         "_userprofile.units", 5, 0,
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
