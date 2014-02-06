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


class SelectUser(QDialog):
    def __init__(self, window = None):
        QDialog.__init__(self, window)
        layout = QGridLayout(dialog)
        layout.addItem(QLabel("User ID"), 0, 0)
        combo = QComboBox()
        view = GrumbleListModel(grumble.Query(User, False), "display_name")
        cb.setModel(view)
        layout.addItem(cb, 0, 1)
        layout.addItem(QLabel("Password"), 1, 0)
        pwd = QLineEdit()
        layout.addItem(pwd, 1, 1)

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
        self.user_id = Config.qtapp.settings.user.user_id
        if not self.select_user():
            self.close()
        
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
        dialog = SelectUser(self)
        self.user_id = dialog.select(self.user_id)
        return self.user_id is not None


class SweatTrails(QApplication):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)

app = SweatTrails(sys.argv)

w = STMainWindow()
w.show()
app.exec_()
sys.exit()

