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
    def __init__(self, query,  prop):
        self._records = None
        self.query = query
        self.prop = prop
        
    def scale(self):
        return self.max() - self.min()

    def offset(self):
        return self.min()
        
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
    
    def value(self,  record):
        return getattr(record, self.prop)

    def __call__(self, record):
        return self.value(record)
        
    def __iter__(self):
        return iter(self.records())

    def __getitem__(self, key):
        return self.records()[key]
        
    def records(self):
        if not self._records:
            if hasattr(self.query, "fetchall") and callable(self.query.fetchall):
                self._records = self.query.fetchall()
            else:
                self._records = [ r for r in self.query ]
        return self._records


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


class Graph(object):
    def __init__(self, **kwargs):
        self._scale = 1.0
        self._offset = 0
        self._color = kwargs.get("color", Qt.black)
        self._style = kwargs.get("style", Qt.SolidLine)
        self._shade = kwargs.get("shade", None)
        self._trendlines = []
        self._polygon = None
        
    def __str__(self):
        return "{:s}(scale = {:f}, offset = {:f})".format(self.__class__.__name__, self._scale, self._offset)

    def scale(self):
        return self.max() - self.min()

    def offset(self):
        return self.min()
        
    def min(self):
        if not hasattr(self,  "_min"):
            self._min = None
            for r in self._axis:
                val = self.y(r)
                self._min = min(val, self._min) if self._min is not None else val
            self._min = self._min or 0
        return self._min
        
    def max(self):
        if not hasattr(self,  "_max"):
            self._max = None
            for r in self._axis:
                self._max = max(self.y(r), self._max)
            self._max = self._max or 0
        return self._max
    
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
    
    def value(self, obj):
        pass
    
    def __call__(self, obj):
        return self.value(obj)
        
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
                QPointF(self.x(obj) - xo, self.y(obj) - yo) for obj in self._axis ]
            if self.shade() is not None:
                points.insert(0, QPointF(points[0].x(), 0))
                points.append(QPointF(points[-1].x(), 0))
            self._polygon = QPolygonF(points)
        return self._polygon
    
    def addTrendLine(self, formula, style = None):
        trendline = (formula
                     if isinstance(formula, Graph)
                     else FormulaGraph(formula, style = style or Qt.SolidLine))
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
        graph._axis = self._axis
        
    def drawGraph(self, graph):
        logger.debug("Drawing graph %s", graph)
        self.painter.save()
        # Set scaling factors. 
        # Scale X so that distance scales to width() - 40: 
        sx = float(self.width() - 40) / float(self._axis.scale()) 
        
        # Scale Y so that elevation diff maps to height() - 40. Y factor
        # is negative so y will actually grow "up":
        sy = - float(self.height() - 40) / float(graph.scale(self._axis)) 
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
