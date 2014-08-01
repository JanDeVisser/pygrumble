'''
Created on Jul 27, 2014

@author: jan
'''


from PySide.QtCore import QCoreApplication
from PySide.QtCore import QThread

from PySide.QtGui import QAction
from PySide.QtGui import QApplication
from PySide.QtGui import QCheckBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QFileDialog
from PySide.QtGui import QFormLayout
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QMainWindow
from PySide.QtGui import QMessageBox
from PySide.QtGui import QTabWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget


import grizzle
import sweattrails.fitparser
import sweattrails.qt.profiletab
import sweattrails.qt.sessiontab
# import sweattrails.qt.usertab

class SelectUser(QDialog):
    def __init__(self, window = None):
        super(SelectUser, self).__init__(window)
        layout = QFormLayout(self)
        self.email = QLineEdit(self)
        fm = self.email.fontMetrics()
        self.email.setMaximumWidth(30 * fm.maxWidth() + 11)
        layout.addRow("&User ID:", self.email)
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)
        fm = self.pwd.fontMetrics()
        self.pwd.setMaximumWidth(30 * fm.width('*') + 11)
        layout.addRow("&Password:", self.pwd)
        self.savecreds = QCheckBox("&Save Credentials (unsafe)")
        layout.addRow(self.savecreds)
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
                "The user ID and password entered do not match.")

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
        parser = sweattrails.fitparser.FITParser(
            QCoreApplication.instance().user, self.fileName)
        parser.setLogger(self.mainWindow)
        parser.parse()

    def parseTCXFile(self):
        pass

    def parseCSVFile(self):
        pass


class STMainWindow(QMainWindow):
    def __init__(self):
        super(STMainWindow, self).__init__()
        self.createActions()
        self.createMenus()
        layout = QVBoxLayout()
        self.sessiontab = sweattrails.qt.sessiontab.SessionTab(self)
        self.profiletab = sweattrails.qt.profiletab.ProfileTab(self)
        self.tabs = QTabWidget()
        self.tabs.currentChanged[int].connect(self.tabChanged)
        self.tabs.addTab(self.sessiontab, "Sessions")
        self.tabs.addTab(self.profiletab, "Profile")
        # if QCoreApplication.instance().user.is_admin():
        #    self.usertab = sweattrails.qt.usertab.UserTab()
        #    self.tabs.addTab(self.usertab, "Users")
        layout.addWidget(self.tabs)
        self.statusbar = QLabel(self)
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
        (fileNames, _) = QFileDialog.getOpenFileNames(self,
                               "Open Activity File",
                               "",
                               "Activity Files (*.tcx *.fit *.csv)")
        if fileNames:
            for f in fileNames:
                t = ImportThread(self, f)
                self.threads.append(t)
                t.start()

    def refresh(self):
        self.sessiontab.refresh()
        self.statusbar.setText("")

    def tabChanged(self, tabix):
        w = self.tabs.currentWidget()
        if hasattr(w, "setValues"):
            w.setValues()

    def log(self, msg):
        self.statusbar.setText(msg)

    def about(self):
        QMessageBox.about(self, "About SweatTrails",
                          "SweatTrails is a training log application")


