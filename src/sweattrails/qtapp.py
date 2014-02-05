# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

from PySide.Qt import InputMethodHint
from PySide.QtGui import QApplication
from PySide.QtGui import QDialog
from PySide.QtGui import QGridLayout
from PySide.QtGui import QInputDialog
from PySide.QtGui import QLineEdit
from PySide.QtGui import QMainWindow
from PySide.QtGui import QTableView

import grumble
import grumble.qt
import grumble.geopt
import grizzle
import sweattrails.config
import sweattrails.session
import gripe.sessionbridge


class STMainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        fileMenu = self.menuBar().addMenu(self.tr("&File"))
        #fileMenu.addAction(Act)
        #fileMenu.addAction(openAct)
        #fileMenu.addAction(saveAct)
        #self.setCentralWidget(self.createTable())
        self._user_manager = grizzle.UserManager()
            
    def show(self):
        super(QMainWindow, self).show()
        user_id = Config.qtapp.settings.user.user_id
        if user_id:
            self.authenticate(user_id)
        else:
            self.select_user()
        
    def authenticate(self, user_id):
        self._user = None
        ok = True
        while ok:
            password, ok = QInputDialog.getText(self, "Authenticate %s" % user_id, "Password", QLineEdit.Password) 
            if ok:
                user = self._user_manager(user_id, password)
                if user:
                    self._user = user
        if not self._user:
            self.select_user()
            
    def select_user(self):
        dialog = QDialog(self)
        layout = QGridLayout(dialog)
        layout.addItem(QLabel("User ID"), 0, 0)
        cb = QComboBox(layout)
        
        layout.addItem(cb, 0, 1)


class SweatTrails(QApplication):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)

app = SweatTrails(sys.argv)

w = STMainWindow()
w.show()
app.exec_()
sys.exit()

