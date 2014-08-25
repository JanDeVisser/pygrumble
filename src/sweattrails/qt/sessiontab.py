'''
Created on Jul 27, 2014

@author: jan
'''

import math

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QSizePolicy 
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import gripe.conversions
import grumble.qt.bridge
import grumble.qt.model
import grumble.qt.view
import sweattrails.config
import sweattrails.session

logger = gripe.get_logger(__name__)

class TimestampColumn(grumble.qt.model.TableColumn):
    def __init__(self, property = "timestamp", **kwargs):
        super(TimestampColumn, self).__init__(property, **kwargs)

    def __call__(self, instance):
        value = getattr(instance, self.name)
        h = int(math.floor(value.seconds / 3600))
        r = value.seconds - (h * 3600)
        m = int(math.floor(r / 60))
        s = r % 60
        if h > 0:
            return "%dh %02d'%02d\"" % (h, m, s)
        else:
            return "%d'%02d\"" % (m, s)


class CPDefColumn(grumble.qt.model.TableColumn):
    def __init__(self, **kwargs):
        super(CPDefColumn, self).__init__("cpdef", **kwargs)

    def __call__(self, instance):
        return instance.cpdef.name


class SessionTypeIcon(grumble.qt.bridge.DisplayConverter):
    def to_display(self, sessiontype, interval):
        icon = sessiontype.icon
        logger.debug("SessionTypeIcon: sessiontype: %s icon %s", sessiontype.name, icon)
        if not icon:
            profile = interval.get_activityprofile()
            node = profile.get_node(sweattrails.config.SessionType, sessiontype.name)
            icon = node.get_root_property("icon")
        if not icon:
            return "image/other.png"
        return icon


class PaceSpeed(grumble.qt.bridge.DisplayConverter):
    def __init__(self, labelprefixes):
        super(PaceSpeed, self).__init__()
        self.labelprefixes = labelprefixes
        
    def label(self, instance):
        if not instance:
            return True
        else:
            session = instance.get_session()
            what = session.sessiontype.speedPace
            prefix = self.labelprefixes.get(what, 
                                            self.labelprefixes.get(None, "")) \
                     if isinstance(self.labelprefixes, dict) \
                     else str(self.labelprefixes)
            return "{prefix} {what}".format(prefix=prefix, what=what)

    def suffix(self, instance):
        if not instance:
            return True
        else:
            session = instance.get_session()
            what = session.sessiontype.speedPace
            units = session.athlete.get_part("userprofile").units
            if what == "Speed":
                return "km/h" if units == "metric" else "mph"
            elif what == "Pace":
                return "min/km" if units == "metric" else "min/mile"
            else:
                return "min/100m" if units == "metric" else "min/100yd"

    def to_display(self, value, instance):
        session = instance.get_session()
        what = session.sessiontype.speedPace
        units = session.athlete.get_part("userprofile").units
        if what == "Speed":
            return "%.1f" % gripe.conversions.ms_to_kmh(value) \
                if units == "metric" \
                else "%.1f" % gripe.conversions.ms_to_mph(value)
        elif what == "Pace":
            return gripe.conversions.ms_to_minkm(value) \
                if units == "metric" \
                else gripe.conversions.ms_to_minmile(value)
        else:
            return "0"


class Distance(grumble.qt.bridge.DisplayConverter):
    def __init__(self):
        super(Distance, self).__init__()
        
    def suffix(self, instance):
        if not instance:
            return True
        else:
            session = instance.get_session()
            what = session.sessiontype.speedPace
            units = session.athlete.get_part("userprofile").units
            if what in ("Speed", "Pace"):
                return "km" if units == "metric" else "miles"
            else:
                return "m" if units == "metric" else "yds"

    def to_display(self, value, instance):
        session = instance.get_session()
        what = session.sessiontype.speedPace
        units = session.athlete.get_part("userprofile").units
        if what in ("Speed", "Pace"):
            d = (value if value else 0) / 1000
            if units != "metric":
                d = gripe.conversions.km_to_mile(d)
            if d < 10:
                return "%.2f" % d
            elif d < 100:
                return "%.1f" % d
            else:
                return "%d" % d
        else:
            return str(value) if value else 0


class ElevationPage(grumble.qt.bridge.FormPage):
    def __init__(self, parent, instance):
        super(ElevationPage, self).__init__(parent)


class CriticalPowerList(grumble.qt.view.TableView):
    def __init__(self, baseform, parent = None):
        super(CriticalPowerList, self).__init__(parent = parent)
        self.baseform = baseform

        query = sweattrails.session.CriticalPower.query(keys_only = False)
        self.setQueryAndColumns(query,
                CPDefColumn(header = "Duration"),
                grumble.qt.model.TableColumn("power", format = "d", header = "Power"),
                TimestampColumn(header = "Starting at"))
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def resetQuery(self):
        self.query().set_parent(self.baseform.instance().intervalpart)


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
        self.addProperty(sweattrails.session.BikePart, "intervalpart.intensity_factor", 4, 0, 
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.tss", 5, 0, 
                         readonly = True)
        
        self.addProperty(sweattrails.session.BikePart, "intervalpart.max_cadence", 0, 2,
                         readonly = True)
        self.addProperty(sweattrails.session.BikePart, "intervalpart.average_cadence", 1, 2, 
                         readonly = True)
        self.cplist = CriticalPowerList(parent, self)
        self.form.addWidget(self.cplist, 6, 0, 1, 2)
        
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


class CriticalPaceList(grumble.qt.view.TableView):
    def __init__(self, baseform, parent = None):
        super(CriticalPaceList, self).__init__(parent = parent)
        self.baseform = baseform

        query = sweattrails.session.RunPace.query(keys_only = False)
        self.setQueryAndColumns(query,
                CPDefColumn(header = "Distance"),
                grumble.qt.model.TableColumn("speed", format = "d", header = "Speed"),
                TimestampColumn(header = "Starting at"))
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def resetQuery(self):
        self.query().set_parent(self.baseform.instance().intervalpart)


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
        self.cplist = CriticalPaceList(parent, self)
        self.form.addWidget(self.cplist, row, 0, 1, 2)
        
    def selected(self):
        self.cplist.refresh()


class RunPlugin(object):
    def __init__(self, page, instance):
        self.page = page
        
    def handle(self, instance):
        logger.debug("Running Run Plugin")
        self.page.addTab(PacesPage(self.page), "Paces")    


class IntervalPage(grumble.qt.bridge.FormWidget):
    def __init__(self, interval, parent = None):
        super(IntervalPage, self).__init__(parent)
        with gripe.db.Tx.begin():
            self.interval = interval
            if isinstance(interval, sweattrails.session.Session):
                self.addProperty(sweattrails.session.Session, "sessiontype", 0, 0, 
                                 readonly = True, has_label = False, rowspan = 3,
                                 bridge = grumble.qt.bridge.Image, height = 64,
                                 displayconverter = SessionTypeIcon())
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
                             readonly = True, displayconverter = Distance())
            row += 1
            self.addProperty(sweattrails.session.Interval, "average_speed", row, col,
                             readonly = True, displayconverter = PaceSpeed("Average"))
            self.addProperty(sweattrails.session.Interval, "max_speed", row, col + 2,
                             readonly = True, 
                             displayconverter = PaceSpeed({"Pace": "Best", "Speed": "Maximum"}))
            row += 1
            self.setInstance(interval)
            self.partSpecificContent(interval)
                    
            if self.interval.geodata:
                self.addTab(ElevationPage(self, interval), "Elevation")
                # TODO Map tab
        
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
        self.session = None
        self.tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.setMinimumSize(600, 600)

    def setSession(self, session):
        self.session = session
        self.tabs.clear()
        self.tabs.addTab(IntervalPage(session, self), str(session.start_time))


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
        self.setMinimumSize(400, 600)

    def resetQuery(self):
        user = QCoreApplication.instance().user
        self.query().clear_filters()
        self.query().add_filter("athlete", "=", user)


class SessionTab(QWidget):
    def __init__(self, parent = None):
        super(SessionTab, self).__init__(parent)
        self.sessions = SessionList(parent = self)
        self.sessions.doubleClicked.connect(self.sessionSelected)
        layout = QHBoxLayout(self)
        layout.addWidget(self.sessions)
        self.details = SessionDetails(self)
        layout.addWidget(self.details)
        self.setLayout(layout)

    def sessionSelected(self, index):
        self.details.setSession(self.sessions.getSelectedObject())

    def refresh(self):
        self.sessions.refresh()

