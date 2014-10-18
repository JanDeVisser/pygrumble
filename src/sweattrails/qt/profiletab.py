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
        self.statusMessage.connect(QCoreApplication.instance().status_message)

    def activate(self):
        if QCoreApplication.instance().user:
            self.setInstance(QCoreApplication.instance().user)


class ZonesPage(QWidget):
    def __init__(self, parent = None):
        super(ZonesPage, self).__init__(parent)
        self.setMinimumSize(800, 600)

    def activate(self):
        pass
    
    
class HealthPage(QWidget):
    def __init__(self, parent = None):
        super(HealthPage, self).__init__(parent)
        self.setMinimumSize(800, 600)

    def activate(self):
        pass
    
    
class ProfileTab(sweattrails.qt.stackedpage.StackedPage):
    def __init__(self, parent = None):
        super(ProfileTab, self).__init__(parent)
        self.addPage("Settings", SettingsPage())
        self.addPage("Zones and FTP", ZonesPage())
        self.addPage("Weight and Health", HealthPage())
