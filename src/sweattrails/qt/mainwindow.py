#
# Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
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

from PySide.QtGui import QAction
from PySide.QtGui import QApplication
from PySide.QtGui import QCheckBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QFileDialog
from PySide.QtGui import QFormLayout
from PySide.QtGui import QIcon
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QMainWindow
from PySide.QtGui import QMessageBox
from PySide.QtGui import QPixmap
from PySide.QtGui import QProgressBar
from PySide.QtGui import QTabWidget
from PySide.QtGui import QValidator
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
# import grizzle
import sweattrails.qt.fitnesstab
import sweattrails.qt.profiletab
import sweattrails.qt.sessiontab
import sweattrails.qt.imports
import sweattrails.qt.usertab

logger = gripe.get_logger(__name__)

class SelectUser(QDialog):
    def __init__(self, window = None):
        super(SelectUser, self).__init__(window)
        layout = QFormLayout(self)
        self.email = QLineEdit(self)
        fm = self.email.fontMetrics()
        self.email.setMaximumWidth(30 * fm.maxWidth() + 11)
        layout.addRow("&User ID:", self.email)
        self.pwd = QLineEdit(self)
        self.pwd.setEchoMode(QLineEdit.Password)
        fm = self.pwd.fontMetrics()
        self.pwd.setMaximumWidth(30 * fm.width('*') + 11)
        layout.addRow("&Password:", self.pwd)
        self.savecreds = QCheckBox("&Save Credentials (unsafe)")
        layout.addRow(self.savecreds)
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, 
            Qt.Horizontal, self)
        self.buttonbox.accepted.connect(self.authenticate)
        self.buttonbox.rejected.connect(self.reject)
        layout.addRow(self.buttonbox)
        self.setLayout(layout)

    def select(self):
        if not QCoreApplication.instance().is_authenticated():
            self.exec_()

    def authenticate(self):
        password = self.pwd.text()
        uid = self.email.text()
        savecreds = self.savecreds.isChecked()
        if QCoreApplication.instance().authenticate(uid, password, savecreds):
            self.accept()
        else:
            QMessageBox.critical(self, "Wrong Password",
                "The user ID and password entered do not match.")


class RepeatPasswordValidator(QValidator):
    def __init__(self, pwdControl):
        super(RepeatPasswordValidator, self).__init__()
        self.pwdControl = pwdControl
        
    def validate(self, input, pos):
        pwd = self.pwdControl.text()
        if len(input) > len(pwd):
            return QValidator.Invalid
        elif input == pwd:
            return QValidator.Acceptable
        elif pwd.startswith(input):
            return QValidator.Intermediate
        else:
            return QValidator.Invalid


class CreateUser(QDialog):
    def __init__(self, window = None):
        super(CreateUser, self).__init__(window)
        layout = QFormLayout(self)
        
        self.email = QLineEdit(self)
        fm = self.email.fontMetrics()
        self.email.setMaximumWidth(30 * fm.maxWidth() + 11)
        layout.addRow("&User ID:", self.email)
        
        self.pwd = QLineEdit(self)
        self.pwd.setEchoMode(QLineEdit.Password)
        fm = self.pwd.fontMetrics()
        self.pwd.setMaximumWidth(30 * fm.width('*') + 11)
        layout.addRow("&Password:", self.pwd)
        
        self.pwd_again = QLineEdit(self)
        self.pwd_again.setEchoMode(QLineEdit.Password)
        fm = self.pwd_again.fontMetrics()
        self.pwd_again.setMaximumWidth(30 * fm.width('*') + 11)
        validator = RepeatPasswordValidator(self.pwd)
        self.pwd_again.setValidator(validator)
        layout.addRow("Password (&again):", self.pwd_again)
        
        self.display_name = QLineEdit(self)
        fm = self.display_name.fontMetrics()
        self.display_name.setMaximumWidth(50 * fm.maxWidth() + 11)
        layout.addRow("&Name", self.display_name)
        
        self.savecreds = QCheckBox("&Save Credentials (unsafe)")
        layout.addRow(self.savecreds)
        
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttonbox.accepted.connect(self.create)
        self.buttonbox.rejected.connect(self.reject)
        layout.addRow(self.buttonbox)
        self.setLayout(layout)

    def create(self):
        password = self.pwd.text()
        if password != self.pwd_again.text():
            QMessageBox.critical(self, "Passwords don't match",
                "The passwords entered are different")
            self.reject()
        try:
            QCoreApplication.instance().add_user(self.email.text(), 
                                                 password,
                                                 self.display_name.text(), 
                                                 self.savecreds.isChecked()) 
            self.accept()
        except Exception as e:
            logger.exception("Exception creating user")
            QMessageBox.critical(self, "Error", str(e))
            self.reject()


class STMainWindow(QMainWindow):
    def __init__(self):
        super(STMainWindow, self).__init__()
        self.createActions()
        self.createMenus()
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.currentChanged[int].connect(self.tabChanged)
        self.sessiontab = sweattrails.qt.sessiontab.SessionTab(self)
        self.tabs.addTab(self.sessiontab, "Sessions")
        self.tabs.addTab(sweattrails.qt.fitnesstab.FitnessTab(self),
                         "Fitness")
        self.tabs.addTab(sweattrails.qt.profiletab.ProfileTab(self),
                         "Profile")
        self.usertab = sweattrails.qt.usertab.UserTab()
        self.tabs.addTab(self.usertab, "Users")
        self.usertab.hide()
        layout.addWidget(self.tabs)
        w = QWidget(self)
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.statusmessage = QLabel()
        self.statusmessage.setMinimumWidth(200)
        self.statusBar().addPermanentWidget(self.statusmessage)
        self.progressbar = QProgressBar()
        self.progressbar.setMinimumWidth(100)
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(100)
        self.statusBar().addPermanentWidget(self.progressbar)
        self.setWindowTitle("SweatTrails")
        self.setWindowIconText("SweatTrails")
        icon = QPixmap("image/sweatdrops.png")
        self.setWindowIcon(QIcon(icon))
        QCoreApplication.instance().refresh.connect(self.userSet)
        
        
    def createActions(self):
        self.switchUserAct = QAction("&Switch User", self, shortcut = "Ctrl+U", statusTip = "Switch User", triggered = self.switch_user)
        self.createUserAct = QAction("&Create User", self, shortcut = "Ctrl+N", statusTip = "Create User", triggered = self.create_user)
        self.importFileAct = QAction("&Import", self, shortcut = "Ctrl+I", statusTip = "Import Session", triggered = self.file_import)
        self.downloadAct = QAction("&Download", self, shortcut = "Ctrl+D", 
                                   statusTip = "Download activities from device", 
                                   triggered = QCoreApplication.instance().download)
        self.exitAct = QAction("E&xit", self, shortcut = "Ctrl+Q", statusTip = "Exit SweatTrails", triggered = self.close)

        self.aboutAct = QAction("&About", self, triggered = self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered = QApplication.aboutQt)


    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.switchUserAct)
        self.fileMenu.addAction(self.createUserAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.importFileAct)
        self.fileMenu.addAction(self.downloadAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)


    def show(self):
        super(QMainWindow, self).show()
        if self.select_user():
            t = sweattrails.qt.imports.ImportThread.get_thread()
            t.importing.connect(self.file_import_started)
            t.imported.connect(self.file_imported)
            t.importerror.connect(self.file_import_error)
        else:
            self.close()

    def switch_user(self):
        pass

    def create_user(self):
        pass

    def select_user(self):
        ret = False
        if QCoreApplication.instance().user:
            return True
        elif QCoreApplication.instance().has_users():
            dialog = SelectUser(self)
            dialog.select()
            ret = QCoreApplication.instance().is_authenticated()
            if ret:
                self.refresh()
        else:
            dialog = CreateUser(self)
            dialog.exec_()
            ret = QCoreApplication.instance().is_authenticated()
            if ret:
                self.refresh()
        return ret

    #
    # FILE IMPORT
    #

    def file_import(self):
        (fileNames, _) = QFileDialog.getOpenFileNames(self,
                               "Open Activity File",
                               "",
                               "Activity Files (*.tcx *.fit *.csv)")
        if fileNames:
            QCoreApplication.instance().import_files(*fileNames)
            
    def file_import_started(self, filename):
        self.switchUserAct.setEnabled(False)
                
    def file_imported(self, filename):
        self.switchUserAct.setEnabled(True)
        self.refresh()

    def file_import_error(self, filename, msg):
        self.switchUserAct.setEnabled(True)
        self.refresh()

    #
    # END FILE IMPORT
    #
    
    # =====================================================================
    # S I G N A L  H A N D L E R S
    # =====================================================================

    def refresh(self):
        QCoreApplication.instance().refresh.emit()
        self.status_message("")

    def tabChanged(self, tabix):
        w = self.tabs.currentWidget()
        if hasattr(w, "setValues"):
            w.setValues()
            
    def userSet(self):
        user = QCoreApplication.instance().user
        if user.is_admin():
            self.usertab.show()

    def status_message(self, msg, *args):
        self.statusmessage.setText(msg.format(*args))

    def progress_init(self, msg, *args):
        self.progressbar.setValue(0)
        self.status_message(msg, *args)

    def progress(self, percentage):
        self.progressbar.setValue(percentage)
        
    def progress_done(self):
        self.progressbar.reset() 

    def about(self):
        QMessageBox.about(self, "About SweatTrails",
                          "SweatTrails is a training log application")
