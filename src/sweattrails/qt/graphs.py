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

class DataSource(object):
    def __init__(self, **kwargs):
        logger.debug("DataSource.__init__ %s", type(self));
        self._records = kwargs.pop("records", None)
        super(DataSource, self).__init__(**kwargs)

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


class QueryDataSource(DataSource):
    def __init__(self, **kwargs):
        logger.debug("QueryDataSource.__init__ %s", type(self));
        self.query = kwargs.pop("query")
        super(QueryDataSource, self).__init__(**kwargs)

    def fetch(self):
        return self.query.fetchall()


class Axis(object):
    def __init__(self, **kwargs):
        logger.debug("Axis.__init__ %s {%s}", type(self), kwargs);
        if "min" in kwargs:
            self._min = kwargs.pop("min")
        if "max" in kwargs:
            self._max = kwargs.pop("max")
        if "value" in kwargs:
            self._value = kwargs.pop("value")
        if "padding" in kwargs:
            self._padding = kwargs.pop("padding")
        if "offset" in kwargs:
            self._offset = kwargs.pop("offset")
        self.prop = kwargs.pop("property", None)
        self._name = kwargs.pop("name", "anon")
        super(Axis, self).__init__(**kwargs)

    def __str__(self):
        return self._name

    def graph(self):
        return self._graph

    def setGraph(self, graph):
        self._graph = graph

    def padding(self):
        if not hasattr(self, "_padding"):
            self._padding = 0.1
            logger.debug("%s.scale(): %s", self, self._padding)
        return self._padding if not callable(self._padding) else self._padding()

    def scale(self):
        if not hasattr(self, "_scale"):
            self._scale = self.max() - self.min()
            self._scale *= 2 * self.padding() if self.min() != 0 else self.padding()
            logger.debug("%s.scale(): %s", self, self._scale)
        return self._scale() if callable(self._scale) else self._scale

    def offset(self):
        if not hasattr(self, "_offset"):
            self._offset = (0
                            if self.min() == 0
                            else self.min() - (self.scale() * self.padding()))
        return self._offset() if callable(self._offset) else self._offset

    def min(self):
        if not hasattr(self, "_min"):
            self._min = None
            ix = 0
            for r in self:
                val = self.value(r)
                self._min = min(val, self._min) if self._min is not None else val
                ix += 1
            self._min = self._min or 0
            logger.debug("%s.min(): %s #=%s", self, self._min, ix)
        return self._min if not callable(self._min) else self._min()

    def max(self):
        if not hasattr(self, "_max"):
            self._max = None
            ix = 0
            for r in self:
                self._max = max(self.value(r), self._max)
                ix += 1
            self._max = self._max or 0
            logger.debug("%s.max(): %s #=%s", self, self._max, ix)
        return self._max if not callable(self._max) else self._max()

    def value(self, record):
        if hasattr(self, "_value"):
            expr = self._value
        else:
            expr = (getattr(record, self.prop)
                    if self.prop and hasattr(record, self.prop)
                    else record)
        ret = expr if not callable(expr) else expr(record)
        ret = ret if ret is not None else 0
        return ret

    def __call__(self, record):
        return self.value(record)

    def __iter__(self):
        return (iter(self.graph().datasource())
                if self.graph().datasource()
                else iter([]))


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


class Series(Axis):
    def __init__(self, **kwargs):
        logger.debug("Series.__init__ %s", type(self));
        self._color = kwargs.pop("color", Qt.black)
        self._style = kwargs.pop("style", Qt.SolidLine)
        self._shade = kwargs.pop("shade", None)
        self._graph = kwargs.pop("graph", None)
        if self._graph:
            self._graph._series.append(self)
        self._trendlines = []
        self._polygon = None
        super(Series, self).__init__(**kwargs)

    def xaxis(self):
        return self._graph.xaxis() if self._graph else None

    def datasource(self):
        return self._graph.ds() if self._graph else None

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
        return self.xaxis()(obj) \
            if self.xaxis() and callable(self.xaxis()) \
            else float(obj)

    def y(self, obj):
        return self(obj)

    def scaleXY(self):
        """
            Calculate painter scaling factors. 

            Scale X so that distance scales to width() - 40: 
        
            Scale Y so that elevation diff maps to height() - 40. Y factor
            is negative so y will actually grow "up".
        """

        return (float(self._graph.width() - 40) / float(self.xaxis().scale()),
                 - float(self._graph.height() - 40) / float(self.scale()))

    def offsetXY(self):
        xoffset = (self.xaxis().offset()
                   if self.xaxis() and
                      hasattr(self.xaxis(), "offset") and
                      callable(self.xaxis().offset)
                   else 0)
        logger.debug("xoffset : %s offset %s", xoffset, self.offset())
        return (20 - xoffset, 20 - self.offset())

    def polygon(self):
        if not self._polygon:
            points = [ QPointF(self.x(obj), self.y(obj)) for obj in self ]
            if self.shade() is not None:
                points.insert(0, QPointF(points[0].x(), 0))
                points.append(QPointF(points[-1].x(), 0))
            self._polygon = QPolygonF(points)
        return self._polygon

    def draw(self):
        logger.debug("Drawing %s", self)
        self._graph.painter.scale(*self.scaleXY())
        self._graph.painter.translate(*self.offsetXY())

        p = QPen(self.color())
        p.setStyle(self.style())
        self._graph.painter.setPen(p)
        if self.shade() is not None:
            self._graph.painter.setBrush(QColor(self.shade()))
            self._graph.painter.drawPolygon(self.polygon())
        else:
            self._graph.painter.drawPolyline(self.polygon())

        for trendline in self.trendLines():
            p = QPen(self.color())
            p.setStyle(trendline.style())
            self._graph.painter.setPen(p)
            self._graph.painter.drawPolyline(trendline.polygon())

    def addTrendLine(self, formula, style = None):
        trendline = (formula
                     if isinstance(formula, Series)
                     else Series(value = formula, style = style or Qt.SolidLine))
        trendline.setGraph(self.graph())
        self._trendlines.append(trendline)

    def trendLines(self):
        return self._trendlines


class Graph(QWidget):
    def __init__(self, parent, ds, **kwargs):
        super(Graph, self).__init__(parent)
        self._ds = ds
        self.setXAxis(ds if ds and hasattr(ds, "value") else None)
        self._series = []
        self.setMinimumSize(350, 300)
        self.update()

    def paintEvent(self, pevent):
        self.draw()

    def setXAxis(self, xaxis):
        self._xaxis = xaxis
        if self._xaxis:
            self._xaxis.setGraph(self)

    def xaxis(self):
        return self._xaxis

    def datasource(self):
        return self._ds

    def addSeries(self, series):
        self._series.append(series)
        series.setGraph(self)

    def series(self):
        return self._series

    def xscale(self):
        return float(self._axis.scale())

    def draw(self):
        self.painter = QPainter(self)
        self.painter.setRenderHint(QPainter.Antialiasing)

        # Set origin to lower left hand corner:
        self.painter.translate(20, self.height() - 20)

        p = QPen(Qt.darkGray)
        p.setStyle(Qt.SolidLine)
        self.painter.setPen(p)
        self.painter.drawLine(0, 0, 0, -self.height() - 20)
        self.painter.drawLine(0, 0, self.width() - 20, 0)

        self.painter.resetTransform()

        for s in self._series:
            self.painter.save()
            s.draw()
            self.painter.restore()
        self.painter = None
