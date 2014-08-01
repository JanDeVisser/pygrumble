'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication
from PySide.QtGui import QFormLayout
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QLineEdit
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import grumble.qt.model
import grumble.qt.view
import sweattrails.session

class SessionPage(QWidget):
    def __init__(self, session, parent = None):
        super(SessionPage, self).__init__(parent)
        self.session = session
        layout = QVBoxLayout()
        self.setLayout(layout)
        hbox = QHBoxLayout()
        form1 = QFormLayout()
        layout.addLayout(hbox)
        hbox.addLayout(form1)
        self.start_time = QLineEdit()
        self.start_time.setText(str(self.session.start_time))
        self.start_time.setReadOnly(True)
        form1.addRow("Date/Time", self.start_time)
        self.description = QLineEdit()
        self.description.setText(self.session.description)
        self.description.setReadOnly(True)
        form1.addRow("Description", self.description)


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
        self.tabs.addTab(SessionPage(session), str(session.start_time))


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

