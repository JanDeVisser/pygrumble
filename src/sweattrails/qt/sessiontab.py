'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication
from PySide.QtCore import Qt

from PySide.QtGui import QSizePolicy 
from PySide.QtGui import QSplitter
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import grumble.qt.bridge
import grumble.qt.model
import grumble.qt.view
import sweattrails.qt.graphs
import sweattrails.session
import sweattrails.qt.view

logger = gripe.get_logger(__name__)


class MiscDataPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent, instance):
        super(MiscDataPage, self).__init__(parent)
        self.row = 0
        if instance.geodata:
            self.addProperty(sweattrails.session.GeoData, "geodata.max_elev", self.row, 0,
                             readonly = True,
                             displayconverter = sweattrails.qt.view.MeterFeet())
            self.addProperty(sweattrails.session.GeoData, "geodata.min_elev", self.row + 1, 0,
                             readonly = True,
                             displayconverter = sweattrails.qt.view.MeterFeet())
            self.addProperty(sweattrails.session.GeoData, "geodata.elev_gain", self.row, 2,
                             readonly = True,
                             displayconverter = sweattrails.qt.view.MeterFeet())
            self.addProperty(sweattrails.session.GeoData, "geodata.elev_loss", self.row + 1, 2,
                             readonly = True,
                             displayconverter = sweattrails.qt.view.MeterFeet())
            self.row += 2
        if instance.max_heartrate:
            self.addProperty(sweattrails.session.Interval, "max_heartrate", self.row, 0, 
                             readonly = True)
            self.addProperty(sweattrails.session.Interval, "average_heartrate", self.row + 1, 0, 
                             readonly = True)
            self.row += 2
        if parent.plugin and hasattr(parent.plugin, "addMiscData"):
            parent.plugin.addMiscData(self, instance)
        if instance.work:
            self.addProperty(sweattrails.session.Interval, "work", self.row, 0, 
                             readonly = True)
            self.row += 1
        if instance.calories_burnt:
            self.addProperty(sweattrails.session.Interval, "calories_burnt", self.row, 0, 
                             readonly = True)
            self.row += 1


class CriticalPowerList(grumble.qt.view.TableView):
    def __init__(self, parent = None, interval = None):
        super(CriticalPowerList, self).__init__(parent = parent)
        self.interval = interval

        query = sweattrails.session.CriticalPower.query(keys_only = False)
        self.setQueryAndColumns(query,
                grumble.qt.model.TableColumn("cpdef.name", header = "Duration"),
                grumble.qt.model.TableColumn("power", format = "d", header = "Power"),
                sweattrails.qt.view.TimestampColumn(header = "Starting on"))
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def resetQuery(self):
        self.query().set_parent(self.interval.intervalpart)


class PowerPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent):
        super(PowerPage, self).__init__(parent)
        logger.debug("Initializing power tab")
        self.addProperty(sweattrails.session.BikePart, "intervalpart.max_power", 0, 0, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.average_power", 1, 0, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.normalized_power", 2, 0, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.vi", 3, 0, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.tss", 3, 2, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.intensity_factor", 4, 0, 
                         readonly = True)
        
        self.addProperty(sweattrails.session.BikePart, "intervalpart.max_cadence", 0, 2,
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.average_cadence", 1, 2, 
                         readonly = True)
        self.cplist = CriticalPowerList(parent, parent.instance())
        self.form.addWidget(self.cplist, 6, 0, 1, 4)
        
    def selected(self):
        self.cplist.refresh()


class BikePlugin(object):
    def __init__(self, page, instance):
        self.page = page
        
    def handle(self, instance):
        logger.debug("Running Bike Plugin")
        part = instance.intervalpart
        if part.max_power:
            self.page.addTab(PowerPage(self.page), "Power")
            
    def addGraphs(self, widget, interval):
        part = interval.intervalpart
        widget.addGraph(sweattrails.qt.graphs.AttrGraph("speed", interval.max_speed, color = Qt.magenta))
        if part.max_power:
            graph = sweattrails.qt.graphs.AttrGraph("power", part.max_power, color = Qt.blue)
            graph.addTrendLine(lambda x : float(part.average_power))
            graph.addTrendLine(lambda x : float(part.normalized_power),
                               Qt.DashDotLine)
            widget.addGraph(graph)
        if part.max_cadence:
            widget.addGraph(sweattrails.qt.graphs.AttrGraph("cadence", part.max_cadence, color = Qt.darkCyan))


class CriticalPaceList(grumble.qt.view.TableView):
    def __init__(self, parent = None, interval = None):
        super(CriticalPaceList, self).__init__(parent = parent)
        self.interval = interval

        query = sweattrails.session.RunPace.query(keys_only = False)
        self.setQueryAndColumns(query,
                grumble.qt.model.TableColumn("cpdef.name", header = "Distance"),
                sweattrails.qt.view.PaceSpeedColumn(interval = interval),
                sweattrails.qt.view.TimestampColumn(header = "Starting on"))
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def resetQuery(self):
        self.query().set_parent(self.interval.intervalpart)


class PacesPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent):
        super(PacesPage, self).__init__(parent)
        logger.debug("Initializing paces tab")
        row = 0
        part = parent.instance().intervalpart
        if part.max_cadence:
            self.addProperty(sweattrails.session.BikePart, "intervalpart.max_cadence", row, 0,
                             readonly = True)
            self.addProperty(sweattrails.session.BikePart, "intervalpart.average_cadence", row + 1, 0, 
                             readonly = True)
            row += 2
        self.cplist = CriticalPaceList(self, parent.instance())
        self.form.addWidget(self.cplist, row, 0, 1, 2)
        
    def selected(self):
        self.cplist.refresh()


class RunPlugin(object):
    def __init__(self, page, instance):
        self.page = page
        
    def handle(self, instance):
        logger.debug("Running Run Plugin")
        self.page.addTab(PacesPage(self.page), "Paces")    

    def addGraphs(self, widget, interval):
        part = interval.intervalpart
        widget.addGraph(sweattrails.qt.graphs.AttrGraph("speed", 
                                                        interval.max_speed,
                                                        color = Qt.magenta))
        if part.max_cadence:
            widget.addGraph(sweattrails.qt.graphs.AttrGraph("cadence", 
                                                            part.max_cadence,
                                                            color = Qt.darkCyan))

    def addMiscData(self, page, interval):
        part = interval.intervalpart
        if part.max_cadence:
            page.addProperty(sweattrails.session.RunPart, 
                             "intervalpart.max_cadence", 
                             page.row, 0, 
                             readonly = True)
            page.addProperty(sweattrails.session.RunPart,
                             "intervalpart.average_cadence",
                             page.row + 1, 0, 
                             readonly = True)
            page.row += 2

class ElevationGraph(sweattrails.qt.graphs.Graph):
    def __init__(self, interval):
        super(ElevationGraph, self).__init__(color = Qt.green)
        self.geodata = interval.geodata
        self._scale = (self.geodata.max_elev - self.geodata.min_elev)
        self._margin = self._scale / 20.0
        self._scale += 2 * self._margin
        self._offset = self.geodata.min_elev - self._margin
        
    def data(self, wp):
        return wp.corrected_elevation \
            if wp.corrected_elevation is not None \
            else wp.elevation if wp.elevation else 0


class WaypointAxis(object):
    def __init__(self, interval):
        self.interval = interval
        with gripe.db.Tx.begin():
            self.waypoints = self.interval.waypoints()
        
    def scale(self):
        return self(self.waypoints[-1]) - self(self.waypoints[0])
    
    def __call__(self, wp):
        return wp.distance
    
    def __iter__(self):
        return iter(self.waypoints)


class GraphPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent, instance):
        super(GraphPage, self).__init__(parent)
        self.graphs = sweattrails.qt.graphs.GraphWidget(
            self, WaypointAxis(instance))
        if instance.max_heartrate:
            self.graphs.addGraph(
                sweattrails.qt.graphs.AttrGraph(
                    self, "hr", instance.max_heartrate, 
                    color = Qt.red))
        if instance.geodata:
            self.graphs.addGraph(ElevationGraph(instance))
        if parent.plugin:
            parent.plugin.addGraphs(self.graphs, instance)
        self.form.addWidget(self.graphs, 0, 0)


class IntervalList(grumble.qt.view.TableView):
    def __init__(self, parent, interval):
        super(IntervalList, self).__init__(parent = parent)
        self.interval = interval

        query = sweattrails.session.Interval.query(
                   parent = self.interval, keys_only = False)
        self.setQueryAndColumns(query,
                sweattrails.qt.view.TimestampColumn(header = "Start Time"),
                sweattrails.qt.view.TimestampColumn("duration", header = "Time"),
                sweattrails.qt.view.DistanceColumn("distance", header = "Distance"),
                sweattrails.qt.view.PaceSpeedColumn("average_speed", interval = interval),
        )
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def resetQuery(self):
        self.query().set_parent(self.interval)


class IntervalListPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent):
        super(IntervalListPage, self).__init__(parent)
        logger.debug("Initializing interval list tab")
        self.list = IntervalList(self, parent.instance())
        self.form.addWidget(self.list, 0, 0)
        self.form.setColumnStretch(0, 1)
        self.form.setRowStretch(0, 1)
        
    def selected(self):
        self.list.refresh()


class IntervalPage(grumble.qt.bridge.FormWidget):
    def __init__(self, interval, parent = None):
        super(IntervalPage, self).__init__(parent)
        with gripe.db.Tx.begin():
            interval = interval()
            self.interval = interval
            if isinstance(interval, sweattrails.session.Session):
                self.addProperty(sweattrails.session.Session, "sessiontype", 0, 0, 
                                 readonly = True, has_label = False, rowspan = 3,
                                 bridge = grumble.qt.bridge.Image, height = 64,
                                 displayconverter = sweattrails.qt.view.SessionTypeIcon())
                self.addProperty(sweattrails.session.Session, "start_time", 0, 1, readonly = True)
                self.addProperty(sweattrails.session.Session, "description", 1, 1, colspan = 3)
                col = 1
                row = 2
            else:
                self.addProperty(sweattrails.session.Interval, "timestamp", 0, 0, colspan = 3,
                                 readonly = True)
                col = 0
                row = 1
            self.addProperty(sweattrails.session.Interval, "elapsed_time", row, col, 
                             readonly = True)
            self.addProperty(sweattrails.session.Interval, "duration", row, col + 2,
                             readonly = True)
            row += 1
            self.addProperty(sweattrails.session.Interval, "distance", row, col,
                             readonly = True, displayconverter = sweattrails.qt.view.Distance())
            row += 1
            self.addProperty(sweattrails.session.Interval, "average_speed", row, col,
                             readonly = True, displayconverter = sweattrails.qt.view.PaceSpeed("Average"))
            self.addProperty(sweattrails.session.Interval, "max_speed", row, col + 2,
                             readonly = True, 
                             displayconverter = sweattrails.qt.view.PaceSpeed({"Pace": "Best", "Speed": "Maximum"}))
            row += 1
            self.setInstance(interval)
            intervals = sweattrails.session.Interval.query(parent = interval).fetchall()
            if len(intervals) > 1:
                page = IntervalListPage(self)
                self.addTab(page, "Intervals")
                page.list.objectSelected.connect(parent.addInterval)
            self.partSpecificContent(interval)
            self.addTab(GraphPage(self, interval), "Graphs")
            self.addTab(MiscDataPage(self, interval), "Other Data")
            self.logmessage.connect(QCoreApplication.instance().log)
            self.setInstance(interval)

    def partSpecificContent(self, instance):
        part = instance.intervalpart
        if not part:
            return
        pluginClass = self.getPartPluginClass(part)
        if pluginClass:
            self.plugin = pluginClass(self, instance)
            self.plugin.handle(instance)
        else:
            self.plugin = None

    _plugins = { 
        sweattrails.session.BikePart: BikePlugin,
        sweattrails.session.RunPart: RunPlugin
    }
    @classmethod
    def getPartPluginClass(cls, part):
        if part.__class__ in cls._plugins:
            return cls._plugins[part.__class__]
        pluginclass = None
        pluginname = gripe.Config.sweattrails.get(part.__class__.__name__)
        if pluginname:
            pluginclass = gripe.resolve(pluginname)
            cls._plugins[part.__class__] = pluginclass
        return pluginclass


class SessionDetails(QWidget):
    def __init__(self, parent = None):
        super(SessionDetails, self).__init__(parent)
        self.tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.setMinimumSize(600, 600)

    def setSession(self, session):
        self.tabs.clear()
        self.tabs.addTab(IntervalPage(session, self), str(session.start_time))

    def addInterval(self, interval):
        self.tabs.addTab(IntervalPage(interval, self), str(interval.timestamp))


class DescriptionColumn(grumble.qt.model.TableColumn):
    def __init__(self):
        super(DescriptionColumn, self).__init__("description")

    def __call__(self, session):
        if not session.description:
            sessiontype = session.sessiontype
            ret = sessiontype.name
        else:
            ret = session.description
        return ret


class SessionList(grumble.qt.view.TableView):
    def __init__(self, user = None, parent = None):
        super(SessionList, self).__init__(parent = parent)

        if not user:
            user = QCoreApplication.instance().user
        query = sweattrails.session.Session.query(keys_only = False)
        query.add_filter("athlete", "=", user)
        query.add_sort("start_time")
        self.setQueryAndColumns(query,
                grumble.qt.model.TableColumn("start_time", format = "%A %B %d", header = "Date"),
                grumble.qt.model.TableColumn("start_time", format = "%H:%M", header = "Time"),
                DescriptionColumn())
        #self.setMinimumSize(400, 600)
        QCoreApplication.instance().refresh.connect(self.refresh)

    def resetQuery(self):
        user = QCoreApplication.instance().user
        self.query().clear_filters()
        self.query().add_filter("athlete", "=", user)


class SessionTab(QSplitter):
    def __init__(self, parent = None):
        super(SessionTab, self).__init__(parent)
        self.sessions = SessionList(parent = self)
        self.addWidget(self.sessions)
        self.details = SessionDetails(self)
        self.sessions.objectSelected.connect(self.details.setSession)
        self.addWidget(self.details)

