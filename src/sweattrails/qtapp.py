# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import sys

from PySide.QtCore import QCoreApplication

from PySide.QtGui import QAction
from PySide.QtGui import QApplication
from PySide.QtGui import QComboBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
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
        layout.addWidget(QLabel("User ID:"), 0, 0)
        self.combo = QComboBox()
        view = grumble.qt.GrumbleListModel(grumble.Query(grizzle.User, False), "display_name")
        self.combo.setModel(view)
        layout.addWidget(self.combo, 0, 1)
        layout.addWidget(QLabel("Password:"), 1, 0)
        self.pwd = QLineEdit()
        layout.addWidget(self.pwd, 1, 1)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.authenticate)
        self.buttonbox.rejected.connect(self.reject)
        layout.addWidget(self.buttonbox, 2, 0, 1, 2)
        self.setLayout(layout)
        self.user_id = None
        self.user = None

    def select(self):
        self.exec_()
        return self.user_id

    def authenticate(self):
        um = QCoreApplication.instance().user_manager()
        password = self.pwd.text()
        uid = self.combo.itemData(self.combo.currentIndex()).name
        user = um.login(uid, password)
        if user:
            self.user_id = uid
            self.user = user
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
        self.switchUserAct = QAction("&Switch User", self, shortcut="Ctrl+U",statusTip="Switch User", triggered=self.switch_user)
        self.createUserAct = QAction("&Create User", self, shortcut="Ctrl+N",statusTip="Create User", triggered=self.create_user)
        self.importFileAct = QAction("&Import", self, shortcut="Ctrl+I",statusTip="Import Session", triggered=self.import_file)
        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q",statusTip="Exit SweatTrails", triggered=self.close)
        
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self,triggered=QApplication.aboutQt)


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
        self.user_id = dialog.select()
        return self.user_id is not None
        
    def import_file(self):
        pass
        
    def about(self):
        QMessageBox.about(self, "About SweatTrails",
                          "SweatTrails is a next-generation training log application")



class SweatTrails(QApplication):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)
        
    def init_config(self):
        config = gripe.Config.qtapp if hasattr(gripe.Config, "qtapp") else {}
        if not hasattr(config, "settings"):
            config.settings = {}
        if not hasattr(config.settings, "user"):
            config.settings.user = { "user_id": None, "password": None }
        gripe.Config.set("qtapp", config)

    def user_manager(self):
        if not hasattr(self, "_user_manager"):
            self._user_manager = grizzle.UserManager()
        return self._user_manager

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

