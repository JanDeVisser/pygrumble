# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import sys

from PySide.QtCore import QCoreApplication
from PySide.QtCore import QThread
from PySide.QtCore import Qt

from PySide.QtGui import QAction
from PySide.QtGui import QApplication
from PySide.QtGui import QCheckBox
from PySide.QtGui import QComboBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QFileDialog
from PySide.QtGui import QFont
from PySide.QtGui import QFormLayout
from PySide.QtGui import QGridLayout
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QInputDialog
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QMainWindow
from PySide.QtGui import QMessageBox
from PySide.QtGui import QPixmap
from PySide.QtGui import QSplashScreen
from PySide.QtGui import QTableView
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import gripe.db
import grumble
import grumble.geopt
import grumble.qt
import grizzle
import sweattrails.fitparser
import sweattrails.config
# import sweattrails.session
# import gripe.sessionbridge


class SplashScreen(QSplashScreen):
    def __init__(self):
        QSplashScreen.__init__(self, QPixmap("image/splash.png"))

class DescriptionColumn(grumble.qt.GrumbleTableColumn):
    def __init__(self):
        super(DescriptionColumn, self).__init__("description")
        
    def __call__(self, session):
        if not session.description:
            sessiontype = session.sessiontype
            ret = sessiontype.name
        else:
            ret = session.description
        return ret

class SessionList(QTableView):
    def __init__(self, parent = None, user = None):
        super(SessionList, self).__init__(parent)

        # set the table model
        if not user:
            user = QCoreApplication.instance().user
        self.q = sweattrails.session.Session.query()
        self.q.add_filter("athlete", "=", user)
        self.q.add_sort("start_time")
        tm = grumble.qt.GrumbleTableModel(self.q,
                grumble.qt.GrumbleTableColumn("start_time", format = "%A %B %d", header = "Date"),
                grumble.qt.GrumbleTableColumn("start_time", format = "%H:%M", header = "Time"),
                DescriptionColumn())
        self.setModel(tm)
        self.setSelectionBehavior(self.SelectRows)

        # set the minimum size
        self.setMinimumSize(400, 600)

        # hide grid
        self.setShowGrid(False)

        # set the font
        # font = QFont("Consolas", 15)
        # self.setFont(font)

        # hide vertical header
        vh = self.verticalHeader()
        vh.setVisible(False)

        # set horizontal header properties
        hh = self.horizontalHeader()
        hh.setStretchLastSection(True)

        # set column width to fit contents
        self.resizeColumnsToContents()

        # set row height
        # nrows = len(self.tabledata)
        # for row in xrange(nrows):
        #    self.setRowHeight(row, 18)

        # enable sorting
        self.setSortingEnabled(True)
        
    def refresh(self):
        user = QCoreApplication.instance().user
        self.model().beginResetModel()
        self.q.clear_filters()
        self.q.add_filter("athlete", "=", user)
        self.model().flush()
        self.model().endResetModel()
        self.resizeColumnsToContents()


class SelectUser(QDialog):
    def __init__(self, window = None):
        QDialog.__init__(self, window)
        layout = QFormLayout(self)
        self.combo = QComboBox()
        view = grumble.qt.GrumbleListModel(grumble.Query(grizzle.User, False), "display_name")
        self.combo.setModel(view)
        layout.addRow("&User ID:", self.combo)
        self.pwd = QLineEdit()
        layout.addRow("&Password:", self.pwd)
        self.savecreds = QCheckBox("&Save Credentials (unsafe)")
        layout.addRow(self.savecreds)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.authenticate)
        self.buttonbox.rejected.connect(self.reject)
        layout.addRow(self.buttonbox)
        self.setLayout(layout)

    def select(self):
        if not QCoreApplication.instance().is_authenticated():
            self.exec_()

    def authenticate(self):
        password = self.pwd.text()
        uid = self.combo.itemData(self.combo.currentIndex()).name
        savecreds = self.savecreds.isChecked()
        if QCoreApplication.instance().authenticate(uid, password, savecreds):
            self.accept()
        else:
            QMessageBox.critical(self, "Wrong Password",
                "The chosen user and the password entered do not match.")

class ImportThread(QThread):
    def __init__(self, mainWindow, fileName):
        super(ImportThread, self).__init__()
        self.fileName = fileName
        self.mainWindow = mainWindow
    
    def run(self):
        self.finished.connect(self.mainWindow.refresh)
        if self.fileName:
            if self.fileName.endswith(".fit"):
                self.parseFITFile()
            elif self.fileName.endswith(".tcx"):
                self.parseTCXFile()
            else:
                self.parseCSVFile()

    def parseFITFile(self):
        parser = sweattrails.fitparser.FITParser(QCoreApplication.instance().user, self.fileName)
        parser.setLogger(self.mainWindow)
        parser.parse()

    def parseTCXFile(self):
        pass

    def parseCSVFile(self):
        pass

class UserTab(QWidget):
    def __init__(self, parent = None):
        super(SessionTab, self).__init__(parent)
        self.sessions = SessionList(self)
        self.sessions.doubleClicked.connect(self.sessionSelected)
        layout = QHBoxLayout(self)
        layout.addWidget(self.sessions)
        self.details = SessionDetails(self)
        layout.addWidget(self.details)
        self.setLayout(layout)


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
        

class SessionTab(QWidget):
    def __init__(self, parent = None):
        super(SessionTab, self).__init__(parent)
        self.sessions = SessionList(self)
        self.sessions.doubleClicked.connect(self.sessionSelected)
        layout = QHBoxLayout(self)
        layout.addWidget(self.sessions)
        self.details = SessionDetails(self)
        layout.addWidget(self.details)
        self.setLayout(layout)

    def sessionSelected(self, index):
        k = self.sessions.model().data(index, Qt.UserRole)
        self.details.setSession(k())

    def refresh(self):
        self.sessions.refresh()

class STMainWindow(QMainWindow):
    def __init__(self):
        super(STMainWindow, self).__init__()
        self.createActions()
        self.createMenus()
        layout = QVBoxLayout()
        self.sessiontab = SessionTab()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.sessiontab, "Sessions")
        layout.addWidget(self.tabs)
        self.statusbar = QLabel()
        layout.addWidget(self.statusbar)
        w = QWidget(self)
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.threads = []

    def createActions(self):
        self.switchUserAct = QAction("&Switch User", self, shortcut = "Ctrl+U", statusTip = "Switch User", triggered = self.switch_user)
        self.createUserAct = QAction("&Create User", self, shortcut = "Ctrl+N", statusTip = "Create User", triggered = self.create_user)
        self.importFileAct = QAction("&Import", self, shortcut = "Ctrl+I", statusTip = "Import Session", triggered = self.import_file)
        self.exitAct = QAction("E&xit", self, shortcut = "Ctrl+Q", statusTip = "Exit SweatTrails", triggered = self.close)

        self.aboutAct = QAction("&About", self, triggered = self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered = QApplication.aboutQt)


    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.switchUserAct)
        self.fileMenu.addAction(self.createUserAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.importFileAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)


    def show(self):
        super(QMainWindow, self).show()
        if not self.select_user():
            self.close()

    def switch_user(self):
        pass

    def create_user(self):
        pass

    def select_user(self):
        dialog = SelectUser(self)
        dialog.select()
        ret = QCoreApplication.instance().is_authenticated()
        if ret:
            self.refresh()
        return ret

    def import_file(self):
        (fileName, _) = QFileDialog.getOpenFileName(self,
                                               "Open Activity File",
                                               "",
                                               "Activity Files (*.tcx *.fit *.csv)")
        if fileName:
            t = ImportThread(self, fileName)
            self.threads.append(t)
            t.start()
            
    def refresh(self):
        self.sessiontab.refresh()
        self.statusbar.setText("")
        
    def log(self, msg):
        self.statusbar.setText(msg)

    def about(self):
        QMessageBox.about(self, "About SweatTrails",
                          "SweatTrails is a next-generation training log application")



class SweatTrails(QApplication):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)

    def init_config(self):
        save = False
        self.user = self.user_id = None
        if "qtapp" not in gripe.Config:
            gripe.Config.qtapp = {}
        self.config = gripe.Config.qtapp
        if "settings" not in self.config:
            self.config["settings"] = {}
            save = True
        if "user" in self.config.settings:
            user_settings = self.config.settings.user
            uid = user_settings.user_id if "user_id" in user_settings else None
            password = user_settings.password if "password" in user_settings else None
            if uid is None or not self.authenticate(uid, password, False):
                del self.config.settings["user"]
                save = True
        if save:
            self.config = gripe.Config.set("qtapp", self.config)

    def user_manager(self):
        if not hasattr(self, "_user_manager"):
            self._user_manager = grizzle.UserManager()
        return self._user_manager

    def authenticate(self, uid, password, savecreds = False):
        self.user = None
        self.user_id = None
        um = self.user_manager()
        ret = False
        with gripe.db.Tx.begin():
            user = um.get(uid)
            hashed = grumble.property.PasswordProperty.hash(password)
            if user.authenticate(password = hashed):
                if savecreds:
                    self.config.settings.user = {
                        "user_id": uid,
                        "password": hashed
                    }
                    self.config = gripe.Config.set("qtapp", self.config)
                self.user_id = uid
                self.user = user
                ret = True
        return ret

    def is_authenticated(self):
        return self.user is not None

app = SweatTrails(sys.argv)
splash = SplashScreen()
app.processEvents()
splash.show()
app.processEvents()
app.init_config()
app.processEvents()

w = STMainWindow()
w.show()
splash.finish(w)

app.exec_()

