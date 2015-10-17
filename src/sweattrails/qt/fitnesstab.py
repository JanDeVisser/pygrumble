#
# Copyright (c) 2015 Jan de Visser (jan@sweattrails.com)
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

from PySide.QtCore import QCoreApplication
from PySide.QtCore import Qt

from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QPushButton
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import grumble.qt.bridge
import grumble.qt.view
import sweattrails.config
import sweattrails.qt.graphs
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
        if user:
            profile = sweattrails.config.ActivityProfile.get_profile(user)
            for cpdef in profile.get_all_linked_references(sweattrails.config.CriticalPace):
                self.tabs.addTab(CriticalPaceTab(self, cpdef), cpdef.name)
        self.setMinimumSize(800, 600)


class BikeFitnessPage(QWidget):
    def __init__(self, parent = None):
        super(BikeFitnessPage, self).__init__(parent)

    def activate(self):
        pass
    
    
class WeightList(grumble.qt.view.TableView):
    def __init__(self, parent):
        super(WeightList, self).__init__(parent = parent)
        user = QCoreApplication.instance().user
        part = user.get_part("WeightMgmt")
        query = sweattrails.userprofile.WeightHistory.query(keys_only = False,
                    parent = part).add_sort("snapshotdate",  False)
        self.setQueryAndColumns(query,
                grumble.qt.model.TableColumn("snapshotdate", format = "%A %B %d %Y", header = "Date"),
                grumble.qt.model.TableColumn("weight"),
                grumble.qt.model.TableColumn("bmi", header = "BMI"),
                grumble.qt.model.TableColumn("bfPercentage", header = "Body fat %"),
                grumble.qt.model.TableColumn("waist"))
        self.setMinimumHeight(150)
        QCoreApplication.instance().refresh.connect(self.refresh)

class WeightPage(QWidget):
    def __init__(self, parent = None):
        super(WeightPage, self).__init__(parent)
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)
        
        user = QCoreApplication.instance().user
        self.part = user.get_part("WeightMgmt")
        query = sweattrails.userprofile.WeightHistory.query(keys_only = False,
                    parent = self.part).add_sort("snapshotdate")
    
        self.graphs = sweattrails.qt.graphs.Graph(
            self, sweattrails.qt.graphs.DateAxis(query, "snapshotdate"))
        self.graphs.addSeries(
            sweattrails.qt.graphs.Series("weight", None, color = Qt.red))
        layout.addWidget(self.graphs)

        self.list = WeightList(self)
        layout.addWidget(self.list)
        buttonWidget = QGroupBox()
        self.buttonbox = QHBoxLayout(buttonWidget)
        self.addbutton = QPushButton("Add", self)
        self.addbutton.clicked.connect(self.addWeightEntry)
        self.buttonbox.addWidget(self.addbutton)
        self.withingsbutton = QPushButton("Download Withings Data", self)
        self.withingsbutton.clicked.connect(self.withingsDownload)
        self.buttonbox.addWidget(self.withingsbutton)
        layout.addWidget(buttonWidget)

    def activate(self):
        pass
        
    def withingsDownload(self):
        job = sweattrails.withings.WithingsJob()
        #job.sync()
        job.jobFinished.connect(self.list.refresh)
        sweattrails.qt.imports.BackgroundThread.add_backgroundjob(job)
        
    def addWeightEntry(self):
        pass


class FitnessTab(sweattrails.qt.stackedpage.StackedPage):
    def __init__(self, parent = None):
        super(FitnessTab, self).__init__(parent)
        self.addPage("Run Fitness", RunFitnessPage(self))
        self.addPage("Bike Fitness", BikeFitnessPage(self))
        self.addPage("Weight", WeightPage(self))
