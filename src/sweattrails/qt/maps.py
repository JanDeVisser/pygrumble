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
from PySide.QtCore import Slot
from PySide.QtCore import Signal

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
    def __init__(self, control, interval):
        super(IntervalJsBridge, self).__init__()
        self.control = control
        self.interval = interval
        
    @Slot()
    def getBoundingBox(self):
        logger.debug("bridge.getBoundingBox")
        box = self.interval.geodata.bounding_box
        ret = []
        ret.extend(box.sw().tuple())
        ret.extend(box.ne().tuple())
        logger.debug("bridge.getBoundingBox ret = %s", ret)
        return ret
    
    @Slot()
    def intervalCount(self):
        q = sweattrails.session.Interval.query(parent = self.interval)
        num = q.count()
        # If there is only one interval, that's the entire session, so
        # there is no separate object for that.
        logger.debug("bridge.intervalCount %s", num if num else 1)
        return num if num else 1
    
    @Slot(int)
    def getLatLons(self, intervalnum):
        ret = []
        if not intervalnum:
            wps = self.interval.waypoints()
            for wp in wps:
                ret.extend(wp.location.tuple())
        else:
            # TODO
            pass
        logger.debug("bridge.getLatLons %s", len(ret))
        return ret
    
    @Slot()
    def drawOverlays(self):
        # TODO
        pass


class IntervalMap(QWebView):
    def __init__(self, parent, interval):
        super(IntervalMap, self).__init__(parent)
        assert interval.geodata, "IntervalMap only works with an interval with geodata"
        self.interval = interval
        self.setContentsMargins(0, 0, 0, 0)
        self.page().view().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAcceptDrops(False)

        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.updateFrame)
        
        self.generateHTML()

    @Slot()
    def updateFrame(self):
        self._bridge = IntervalJsBridge(self, self.interval)
        self.page().mainFrame().addToJavaScriptWindowObject("bridge", self._bridge);

    def generateHTML(self):
        with open("sweattrails/qt/maps.html") as fd:
            html = fd.read()
            templ = string.Template(html)
            html = templ.substitute(
                bgcolor = "#343434", 
                fgcolor = "#FFFFFF", 
                mapskey = gripe.Config.app["config"].google_api_key)
            self.page().mainFrame().setHtml(html);

