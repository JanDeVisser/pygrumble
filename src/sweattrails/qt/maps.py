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

import os.path

from PyQt5.QtCore import QObject
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import pyqtSlot

from PyQt5.QtWidgets import QSizePolicy

from PyQt5.QtWebKitWidgets import QWebPage
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebView

import gripe
import sweattrails.session

logger = gripe.get_logger(__name__)


class IntervalJsBridge(QObject):
    def __init__(self, control, interval):
        super(IntervalJsBridge, self).__init__()
        self.control = control
        self.interval = interval
        with gripe.db.Tx.begin():
            q = sweattrails.session.Interval.query(parent = self.interval)
            q.add_sort("timestamp")
            self._intervals = [i for i in q]
            self._wps = self.interval.waypoints()
            
    @pyqtSlot(result = str)
    def getConfig(self):
        return gripe.Config.as_json()

    @pyqtSlot(result = 'QVariantList')
    def getBoundingBox(self):
        box = self.interval.geodata.bounding_box
        ret = []
        ret.extend(box.sw().tuple())
        ret.extend(box.ne().tuple())
        return ret
    
    @pyqtSlot(result = int)
    def intervalCount(self):
        num = len(self._intervals)
        # If there is only one interval, that's the entire session, so
        # there is no separate object for that.
        return num if num else 1
    
    @pyqtSlot(int, result = 'QVariantList')
    def getLatLons(self, intervalnum):
        if not intervalnum:
            i = self.interval
        else:
            if not self._intervals and intervalnum == 1:
                i = self.interval
            else:
                assert intervalnum <= len(self._intervals)
                i = self._intervals[intervalnum - 1]
        ret = []
        for wp in (wp for wp in i.waypoints(self._wps) if wp.location):
            ret.extend(wp.location.tuple())
        return ret
    
    @pyqtSlot()
    def drawOverlays(self):
        self.control.drawShadedRoute()
        pass
    
    @pyqtSlot(int)
    def toggleInterval(self, intervalnum):
        pass
    
    @pyqtSlot(str)
    def log(self, msg):
        logger.info("JS-Bridge: %s", msg)


class ConsoleLoggerWebPage(QWebPage):
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logger.debug("JS-Console (%s/%d): %s", sourceID, lineNumber, message)


class IntervalMap(QWebView):
    def __init__(self, parent, interval):
        super(IntervalMap, self).__init__(parent)
        #assert interval.geodata, "IntervalMap only works with an interval with geodata"
        self.interval = interval
        self.setContentsMargins(0, 0, 0, 0)
        self.setPage(ConsoleLoggerWebPage())
        QWebSettings.globalSettings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.page().view().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAcceptDrops(False)

        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.updateFrame)

    @pyqtSlot()
    def updateFrame(self):
        self._bridge = IntervalJsBridge(self, self.interval)
        self.page().mainFrame().addToJavaScriptWindowObject("bridge", self._bridge);

    @pyqtSlot()
    def drawMap(self):
        #=======================================================================
        # with open("sweattrails/qt/maps.html") as fd:
        #     html = fd.read()
        #     templ = string.Template(html)
        #     html = templ.substitute(
        #         bgcolor = "#343434", 
        #         fgcolor = "#FFFFFF", 
        #         mapskey = gripe.Config.app["config"].google_api_key)
        #=======================================================================
        self.setUrl(QUrl.fromLocalFile(os.path.join(gripe.root_dir(), "sweattrails/qt/maps.html")))

    def drawShadedRoute(self):
        pass
