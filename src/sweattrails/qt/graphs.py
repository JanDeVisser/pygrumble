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

import datetime

from PySide.QtCore import QPointF
from PySide.QtCore import Qt

from PySide.QtGui import QColor
from PySide.QtGui import QPainter
from PySide.QtGui import QPen
from PySide.QtGui import QPolygonF
from PySide.QtGui import QWidget

import gripe

logger = gripe.get_logger(__name__)

class Axis(object):
    def __init__(self, **kwargs):
        if "min" in kwargs:
            self._min = kwargs["min"]
        if "max" in kwargs:
            self._min = kwargs["min"]
        if "value" in kwargs:
            self._value = value
        self.prop = kwargs.get("property")

    def scale(self):
        if not hasattr(self, "_scale"):
            self._scale = self.max() - self.min()
            self._scale *= 1.2 if self.min() != 0 else 1.1
        return self.scale()

    def offset(self):
        return 0 if self.min() == 0 else self.min() - (self.scale() * 0.1)
        
    def min(self):
        if not hasattr(self,  "_min"):
            self._min = None
            for r in self:
                val = self.value(r)
                self._min = min(val, self._min) if self._min is not None else val
            self._min = self._min or 0
        return self._min
        
    def max(self):
        if not hasattr(self,  "_max"):
            self._max = None
            for r in self:
                self._max = max(self.value(r), self._max)
            self._max = self._max or 0
        return self._max
    
    def value(self, record):
        if hasattr(self, _value):
            expr = self._value
        else:
            expr = (getattr(record, self.prop)
                    if self.prop and hasattr(record, self.prop)
                    else record)
        return expr if not callable(expr) else expr(record)

    def __call__(self, record):
        return self.value(record)


class XAxis(Axis):
    def __init__(self, **kwargs):
        super(XAxis, self).__init__(**kwargs)
        self._records = kwargs.get("records")
        
    def __iter__(self):
        return iter(self.records())

    def __getitem__(self, key):
        return self.records()[key]
        
    def fetch(self):
        return []

    def records(self):
        if not self._records:
            self._records = self.fetch()
        return self._records


class QueryAxis(XAxis):
    def __init__(self, query, **kwargs):
        super(QueryAxis, self).__init__(property = prop, **kwargs)
        self.query = query

    def fetch(self):
        return self.query.fetchall()


class DateAxis(Axis):
    def min(self):
        return self.todate(super(DateAxis, self).min())
    
    def max(self):
        return self.todate(super(DateAxis, self).max())
    
    def __call__(self, record):
        return (self.todate(self.value(record)) - self.min()).days
        
    @staticmethod
    def todate(val):
        return val if isinstance(val, datetime.date) else val.date()


class Graph(Axis):
    def __init__(self, **kwargs):
        super(Graph, self).__init__(**kwargs)
        self._axis = kwargs.get("axis")
        self._color = kwargs.get("color", Qt.black)
        self._style = kwargs.get("style", Qt.SolidLine)
        self._shade = kwargs.get("shade", None)
        self._trendlines = []
        self._polygon = None
        
    def __iter__(self):
        return iter(self._axis)

    def setColor(self, color):
        self._color = color
        
    def color(self):
        return self._color
    
    def style(self):
        return self._style
    
    def setStyle(self, style):
        self._style = style
        
    def shade(self):
        return self._shade

    def setShade(self, shade):
        self._shade = bool(shade)
    
    def x(self, obj):
        return self._axis(obj) if callable(self._axis) else float(obj)
        
    def y(self, obj):
        self(obj) - self.offset()
        
    def polygon(self):
        if not self._polygon:
            xo = self._axis.offset() \
                if hasattr(self._axis) and callable(self._axis.offset) \
                else 0
            yo = self.offset()
            points = [ 
                QPointF(self.x(obj) - xo, self.y(obj) - yo) for obj in self ]
            if self.shade() is not None:
                points.insert(0, QPointF(points[0].x(), 0))
                points.append(QPointF(points[-1].x(), 0))
            self._polygon = QPolygonF(points)
        return self._polygon
    
    def addTrendLine(self, formula, style = None):
        trendline = (formula
                     if isinstance(formula, Graph)
                     else Graph(value = formula, style = style or Qt.SolidLine))
        trendline._axis = self._axis
        self._trendlines.append(trendline)
        
    def trendLines(self):
        return self._trendlines


class FormulaGraph(Graph):
    def __init__(self, formula, **kwargs):
        super(FormulaGraph, self).__init__(**kwargs)
        self._formula = formula
        
    def value(self, object):
        return self._formula(object)


class GraphWidget(QWidget):
    def __init__(self, parent, axis):
        super(GraphWidget, self).__init__(parent)
        self._axis = axis
        self._graphs = []
        self.setMinimumSize(350, 300)
        self.update()
        
    def addGraph(self, graph):
        self._graphs.append(graph)
        graph._axis = self._axis
        
    def drawGraph(self, graph):
        logger.debug("Drawing graph %s", graph)
        self.painter.save()
        # Set scaling factors. 
        # Scale X so that distance scales to width() - 40: 
        sx = float(self.width() - 40) / float(self._axis.scale()) 
        
        # Scale Y so that elevation diff maps to height() - 40. Y factor
        # is negative so y will actually grow "up":
        sy = - float(self.height() - 40) / float(graph.scale()) 
        #logger.debug("Scaling factors %f, %f", sx, sy)
        self.painter.scale(sx, sy)
      
        points = graph.polygon()
        p = QPen(graph.color())
        p.setStyle(graph.style())
        self.painter.setPen(p)
        if graph.shade() is not None:
            self.painter.setBrush(QColor(graph.shade()))
            self.painter.drawPolygon(points)
        else:            
            self.painter.drawPolyline(points)
        
        for trendline in graph.trendLines():
            p = QPen(graph.color())
            p.setStyle(trendline.style())
            self.painter.setPen(p)
            points = trendline.polygon()
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
