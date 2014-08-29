'''
Created on Aug 28, 2014

@author: jan
'''

from PySide.QtCore import QPoint
from PySide.QtCore import Qt

from PySide.QtGui import QPainter
from PySide.QtGui import QPolygon
from PySide.QtGui import QWidget

import gripe
import grumble.qt.bridge

logger = gripe.get_logger(__name__)

class Graph(object):
    def __init__(self, interval):
        self.interval = interval
        self._scale = 1.0
        self._offset = 0

    def scale(self, waypoints):
        return self._scale

    def offset(self, waypoints):
        return self._offset
    
    def data(self, wp):
        pass

    
class AttrGraph(Graph):
    def __init__(self, attr, interval, max_value = 0):
        super(AttrGraph, self).__init__(interval)
        self._attr = attr
        self._scale = max_value
        self._margin = self._scale / 20
        self._scale += self._margin

    def data(self, wp):
        return getattr(wp, self._attr) or 0


class ElevationGraph(AttrGraph):
    def __init__(self, interval):
        super(ElevationGraph, self).__init__("altitude", interval)
        self.geodata = interval.geodata
        self._scale = (self.geodata.max_elev - self.geodata.min_elev)
        self._margin = self._scale / 20
        self._scale += 2 * self._margin
        self._offset = self.geodata.min_elev - self._margin


class GraphWidget(QWidget):
    def __init__(self, parent, interval):
        super(GraphWidget, self).__init__(parent)
        self.interval = interval
        self.w = self.interval.distance
        self._graphs = []
        with gripe.db.Tx.begin():
            self.waypoints = self.interval.waypoints()
        self.setMinimumSize(350, 300)
        self.update()
        
    def addGraph(self, graph):
        self._graphs.append(graph)
        
    def drawGraph(self, graph, painter, color):
        painter.save()
        # Set scaling factors. 
        # Scale X so that distance scales to width() - 40: 
        sx = float(self.width() - 40) / float(self.w) 
        
        # Scale Y so that elevation diff maps to height() - 40. Y factor
        # is negative so y will actually grow "up":
        sy = - float(self.height() - 40) / float(graph.scale(self.waypoints)) 
        #logger.debug("Scaling factors %f, %f", sx, sy)
        painter.scale(sx, sy)
        offset = graph.offset(self.waypoints)
        
        painter.setPen(color)
        points = QPolygon(
            [ QPoint(wp.distance, graph.data(wp) - offset)
                for wp in self.waypoints])
        painter.drawPolyline(points)
        painter.restore()

    def paintEvent(self, pevent):
        #logger.debug("ElevationGraph paintEvent, size: %d, %d; w,h: %d, %d", self.width(), self.height(), self.w, self.h)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set origin to lower left hand corner:
        painter.translate(20, self.height() - 20)
        
        painter.setPen(Qt.lightGray)
        painter.setPen(Qt.SolidLine)
        painter.drawLine(0, 0, 0, - self.height() - 20)
        painter.drawLine(0, 0, self.width() - 20, 0)
        
        colors = [ Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.darkCyan ]
        for ix in range(len(self._graphs)):
            self.drawGraph(self._graphs[ix], painter, colors[ix])


class GraphPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent, instance):
        super(GraphPage, self).__init__(parent)
        self.graphs = GraphWidget(self, instance)
        if instance.max_heartrate:
            self.graphs.addGraph(AttrGraph(self, "hr", instance, instance))
        if instance.geodata:
            self.graphs.addGraph(ElevationGraph(instance))
        if parent.plugin:
            parent.plugin.addGraphs(self.graphs, instance)
        self.form.addWidget(self.graphs, 0, 0)


