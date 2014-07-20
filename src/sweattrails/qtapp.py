# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import sys

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QAction
from PySide.QtGui import QApplication
from PySide.QtGui import QCheckBox
from PySide.QtGui import QComboBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QFileDialog
from PySide.QtGui import QGridLayout
from PySide.QtGui import QInputDialog
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QMainWindow
from PySide.QtGui import QMessageBox
from PySide.QtGui import QPixmap
from PySide.QtGui import QSplashScreen
from PySide.QtGui import QTableView

import gripe
import gripe.db
import grumble
import grumble.qt
import grumble.geopt
import grizzle
import sweattrails.config
# import sweattrails.session
# import gripe.sessionbridge


class SplashScreen(QSplashScreen):
    def __init__(self):
        QSplashScreen.__init__(self, QPixmap("image/splash.png"))

class SelectUser(QDialog):
    def __init__(self, window = None):
        QDialog.__init__(self, window)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("&User ID:"), 0, 0)
        self.combo = QComboBox()
        view = grumble.qt.GrumbleListModel(grumble.Query(grizzle.User, False), "display_name")
        self.combo.setModel(view)
        layout.addWidget(self.combo, 0, 1)
        layout.addWidget(QLabel("&Password:"), 1, 0)
        self.pwd = QLineEdit()
        layout.addWidget(self.pwd, 1, 1)
        self.savecreds = QCheckBox("&Save Credentials (unsafe)")
        layout.addWidget(self.savecreds, 2, 0, 1, 2)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.authenticate)
        self.buttonbox.rejected.connect(self.reject)
        layout.addWidget(self.buttonbox, 3, 0, 1, 2)
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

class STMainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.createActions()
        self.createMenus()
        # self.setCentralWidget(self.createTable())

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
        return QCoreApplication.instance().is_authenticated()

    def import_file(self):
        (fileName, _) = QFileDialog.getOpenFileName(self,
                                               "Open Activity File",
                                               "",
                                               "Activity Files (*.tcx *.fit *.csv)")
        print fileName, filter
        if fileName:
            if fileName.endswith(".fit"):
                self.parseFITFile(fileName)
            elif fileName.endswith(".tcx"):
                self.parseTCXFile(fileName)
            else:
                self.parseCSVFile(fileName)

    def parseFITFile(self, fileName):
        pass

    def parseTCXFile(self, fileName):
        pass

    def parseCSVFile(self, fileName):
        pass

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
splash.show()
app.processEvents()
app.init_config()
app.processEvents()

w = STMainWindow()
w.show()
splash.finish(w)

app.exec_()

