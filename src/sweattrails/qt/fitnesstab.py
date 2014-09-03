'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import grumble.qt.bridge
import grumble.qt.view
import sweattrails.config
import sweattrails.qt.stackedpage
import sweattrails.qt.view

logger = gripe.get_logger(__name__)


class BestPaceList(grumble.qt.view.TableView):
    def __init__(self, parent, cpdef):
        super(BestPaceList, self).__init__(parent = parent)
        self.cpdef = cpdef
        query = sweattrails.session.BestRunPace.query(keys_only = False,
                    parent = self.cpdef).add_sort("snapshotdate")
        self.setQueryAndColumns(query,
                grumble.qt.model.TableColumn("snapshotdate", format = "%A %B %d", header = "Date"),
                grumble.qt.model.TableColumn("cpdef.name", header = "Distance"),
                sweattrails.qt.view.PaceSpeedColumn(what = "Pace"))
        self.setMinimumHeight(150)
        QCoreApplication.instance().refresh.connect(self.refresh)

    def resetQuery(self):
        self.query().set_parent(self.cpdef)


class CriticalPaceTab(QWidget):
    def __init__(self, parent, cpdef):
        super(CriticalPaceTab, self).__init__(parent)
        self.cpdef = cpdef
        layout = QVBoxLayout(self)
        self.list = BestPaceList(self, cpdef)
        layout.addWidget(self.list)

class RunFitnessPage(QWidget):
    def __init__(self, parent = None):
        super(RunFitnessPage, self).__init__(parent)
        layout = QHBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        user = QCoreApplication.instance().user
        profile = sweattrails.config.ActivityProfile.get_profile(user)
        for cpdef in profile.get_all_linked_references(sweattrails.config.CriticalPace):
            self.tabs.addTab(CriticalPaceTab(self, cpdef), cpdef.name)
        self.setMinimumSize(800, 600)


class BikeFitnessPage(QWidget):
    def __init__(self, parent = None):
        super(BikeFitnessPage, self).__init__(parent)

    def activate(self):
        pass
    
    
class WeightPage(QWidget):
    def __init__(self, parent = None):
        super(WeightPage, self).__init__(parent)
        self.setMinimumSize(800, 600)

    def activate(self):
        pass


class FitnessTab(sweattrails.qt.stackedpage.StackedPage):
    def __init__(self, parent = None):
        super(FitnessTab, self).__init__(parent)
        self.addPage("Run Fitness", RunFitnessPage())
        self.addPage("Bike Fitness", BikeFitnessPage())
        self.addPage("Weight", WeightPage())
