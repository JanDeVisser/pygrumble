'''
Created on Jul 27, 2014

@author: jan
'''

import math

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe.conversions
import grumble.qt.bridge
import grumble.qt.model
import grumble.qt.view
import sweattrails.session

class TimeDeltaDisplayConverter(grumble.qt.bridge.DisplayConverter):
    def to_display(self, value, instance):
        h = int(math.floor(value.seconds / 3600))
        r = value.seconds - (h * 3600)
        m = int(math.floor(r / 60))
        s = r % 60
        if h > 0:
            return "%dh %02d'%02d\"" % (h, m, s)
        else:
            return "%d'%02d\"" % (m, s)

class PaceSpeed(grumble.qt.bridge.DisplayConverter):
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


class IntervalPage(grumble.qt.bridge.FormWidget):
    def __init__(self, interval, parent = None):
        super(IntervalPage, self).__init__(parent)
        if isinstance(interval, sweattrails.session.Session):
            self.addProperty(sweattrails.config.SessionType, "sessiontype.name", readonly = True)
            self.addProperty(sweattrails.session.Session, "start_time", readonly = True)
            self.addProperty(sweattrails.session.Session, "description")
        else:
            self.addProperty(sweattrails.session.Interval, "timestamp",
                             readonly = True, displayconverter = TimeDeltaDisplayConverter())
        self.addProperty(sweattrails.session.Interval, "elapsed_time",
                         readonly = True, displayconverter = TimeDeltaDisplayConverter())
        self.addProperty(sweattrails.session.Interval, "duration",
                         readonly = True, displayconverter = TimeDeltaDisplayConverter())
        self.addProperty(sweattrails.session.Interval, "distance",
                         readonly = True, displayconverter = Distance())
        self.addProperty(sweattrails.session.Interval, "average_speed",
                         readonly = True, displayconverter = PaceSpeed())
        self.addProperty(sweattrails.session.Interval, "max_speed",
                         readonly = True, displayconverter = PaceSpeed())
        self.logmessage.connect(QCoreApplication.instance().log)
        self.setInstance(interval)


class SessionDetails(QWidget):
    def __init__(self, parent = None):
        super(SessionDetails, self).__init__(parent)
        self.session = None
        self.tabs = QTabWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)
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

