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
# This module uses ideas and code from GoldenCheetah:
# Copyright (c) 2009 Greg Lonnon (greg.lonnon@gmail.com)
#               2011 Mark Liversedge (liversedge@gmail.com)

import string

from PySide.QtCore import QCoreApplication
from PySide.QtCore import QObject
from PySide.QtCore import Qt
from PySide.QtCore import QUrl

from PySide.QtGui import QSizePolicy 
from PySide.QtGui import QWidget

from PySide.QtWebKit import QWebView

import gripe
import grumble.qt.bridge
import grumble.qt.model
import grumble.qt.view
import sweattrails.session
import sweattrails.qt.view

logger = gripe.get_logger(__name__)


class IntervalJsBridge(QObject):
    def __init__(self, control):
        super(IntervalJsBridge, self).__init__()
        self.control = control
        
    def getBoundingBox(self):
        gd = xx

class IntervalMap(QWebView):
    def __init__(self, parent, interval):
        super(IntervalMap, self).__init__(parent)
        self.interval = interval
        self.setContentsMargins(0, 0, 0, 0)
        self.page().view().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAcceptDrops(False)

        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.updateFrame)
        
        self.generateHTML()

    def updateFrame(self):
        self._bridge = IntervalJsBridge(self.interval)
        self.page().mainFrame().addToJavaScriptWindowObject("bridge", self._bridge);

    def generateHTML(self):
        with open("sweattrails/qt/maps.html") as fd:
            html = fd.read()
            templ = string.Template(html)
            html = templ.substitute(
                bgcolor = xx, 
                fgcolor = yy, 
                mapskey = zz)
            self.page().mainFrame().setHtml(html);

