'''
Created on Aug 28, 2014

@author: jan
'''

from PySide.QtCore import QPointF
from PySide.QtCore import Qt

from PySide.QtGui import QPainter
from PySide.QtGui import QPen
from PySide.QtGui import QPolygonF
from PySide.QtGui import QWidget

import gripe

logger = gripe.get_logger(__name__)

class Graph(object):
    def __init__(self, **kwargs):
        self._scale = 1.0
        self._offset = 0
        self._color = kwargs.get("color", Qt.black)
        self._style = kwargs.get("style", Qt.SolidLine)
        self._trendlines = []
        self._polygon = None
        
    def __str__(self):
        return "{:s}(scale = {:f}, offset = {:f})".format(self.__class__.__name__, self._scale, self._offset)

    def scale(self, objects):
        return self._scale

    def offset(self, objects):
        return self._offset
    
    def setColor(self, color):
        self._color = color
        
    def color(self):
        return self._color
    
    def style(self):
        return self._style
    
    def setStyle(self, style):
        self._style = style
    
    def data(self, obj):
        pass
    
    def __call__(self, obj):
        return self.data(obj)
    
    def polygon(self, axis):
        if not self._polygon:
            o = self.offset(axis)
            self._polygon = QPolygonF(
                [ QPointF(axis(obj) if callable(axis) else obj, self(obj) - o)
                    for obj in axis])
        return self._polygon
    
    def addTrendLine(self, formula, style = None):
        trendline = (formula
                     if isinstance(formula, Graph)
                     else FormulaGraph(formula, style = style or Qt.SolidLine))
        self._trendlines.append(trendline)
        
    def trendLines(self):
        return self._trendlines


class FormulaGraph(Graph):
    def __init__(self, formula, **kwargs):
        super(FormulaGraph, self).__init__(**kwargs)
        self._formula = formula
        
    def data(self, object):
        return self._formula(object)


class AttrGraph(Graph):
    def __init__(self, attr, max_value = 0, **kwargs):
        super(AttrGraph, self).__init__(**kwargs)
        self._attr = attr
        self._scale = float(max_value)
        self._margin = self._scale / 20.0
        self._scale += self._margin

    def __str__(self):
        return "{:s}(color = {:s}, style = {:s}, attr = {:s}, scale = {:f}, offset = {:f})".format(
            self.__class__.__name__, self.color(), self.style(), self._attr, self._scale, self._offset)

    def data(self, obj):
        return getattr(obj, self._attr) or 0


class GraphWidget(QWidget):
    def __init__(self, parent, axis):
        super(GraphWidget, self).__init__(parent)
        self._axis = axis
        self._graphs = []
        self.setMinimumSize(350, 300)
        self.update()
        
    def addGraph(self, graph):
        self._graphs.append(graph)
        
    def drawGraph(self, graph):
        # logger.debug("Drawing graph %s", graph)
        self.painter.save()
        # Set scaling factors. 
        # Scale X so that distance scales to width() - 40: 
        sx = float(self.width() - 40) / float(self._axis.scale()) 
        
        # Scale Y so that elevation diff maps to height() - 40. Y factor
        # is negative so y will actually grow "up":
        sy = - float(self.height() - 40) / float(graph.scale(self._axis)) 
        #logger.debug("Scaling factors %f, %f", sx, sy)
        self.painter.scale(sx, sy)
        
        p = QPen(graph.color())
        p.setStyle(graph.style())
        self.painter.setPen(p)
        points = graph.polygon(self._axis)
        self.painter.drawPolyline(points)
        
        step = 1/sx
        for trendline in graph.trendLines():
            p = QPen(graph.color())
            p.setStyle(trendline.style())
            self.painter.setPen(p)
            points = trendline.polygon(
                (x*step for x in range(self.width() - 39))
            )
            self.painter.drawPolyline(points)
        self.painter.restore()

    def paintEvent(self, pevent):
        self.painter = QPainter(self)
        self.painter.setRenderHint(QPainter.Antialiasing)
        
        # Set origin to lower left hand corner:
        self.painter.translate(20, self.height() - 20)
        
        p = QPen(Qt.darkGray)
        p.setStyle(Qt.SolidLine)
        self.painter.setPen(p)
        self.painter.drawLine(0, 0, 0, - self.height() - 20)
        self.painter.drawLine(0, 0, self.width() - 20, 0)
        
        for graph in self._graphs:
            self.drawGraph(graph)
        self.painter = None
