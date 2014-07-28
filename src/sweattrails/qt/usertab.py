'''
Created on Jul 27, 2014

@author: jan
'''

from PySide.QtGui import QCheckBox
from PySide.QtGui import QComboBox
from PySide.QtGui import QFormLayout
from PySide.QtGui import QGroupBox
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QLabel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QPushButton
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QWidget

import gripe
import gripe.db
import grizzle
import grumble.qt

class UserList(grumble.qt.GrumbleTableView):
    def __init__(self, parent = None):
        super(UserList, self).__init__(parent = parent)
        query = grizzle.User.query(keys_only = False)
        query.add_sort("email")
        self.setQueryAndColumns(query, "email", "display_name", "status")
        self.setMinimumSize(400, 600)
        

class UserDetails(QWidget):
    def __init__(self, user, parent = None):
        super(UserDetails, self).__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        form1 = QFormLayout()
        layout.addLayout(form1)
        self.email = QLineEdit(self)
        self.email.setReadOnly(True)
        form1.addRow("User email:", self.email)
        self.display_name = QLineEdit(self)
        self.display_name.setReadOnly(True)
        form1.addRow("Display Name:", self.display_name)
        hbox = QHBoxLayout()
        self.status = QComboBox(self)
        for s in grizzle.UserStatus:
            self.status.addItem(s)
        self.status.hide()
        self.statuslabel = QLabel()
        hbox.addWidget(self.status)
        hbox.addWidget(self.statuslabel)
        form1.addRow("Status:", hbox)
        rolebox = QGroupBox("Roles", self)
        rb_layout = QVBoxLayout()
        self.roles = {}
        for (role, definition) in gripe.Config.app.roles.items():
            cb = QCheckBox(definition.label, self)
            #cb.setCheckable(False)
            self.roles[role] = (definition, cb)
            rb_layout.addWidget(cb)
        rolebox.setLayout(rb_layout)
        form1.addRow(rolebox)
        self.setUser(user)

    def setUser(self, user):
        with gripe.db.Tx.begin():
            self.user = user
            self.email.setText(user.email)
            self.display_name.setText(user.display_name)
            self.status.setEditText(user.status)
            self.statuslabel.setText(user.status)
            for (role, (_, cb)) in self.roles.items():
                cb.setChecked(role in user.has_roles)


class UserTab(QWidget):
    def __init__(self, parent = None):
        super(UserTab, self).__init__(parent)
        self.users = UserList(self)
        self.users.doubleClicked.connect(self.userSelected)
        layout = QHBoxLayout()
        vbox = QVBoxLayout()
        layout.addLayout(vbox)
        vbox.addWidget(self.users)
        self.addButton = QPushButton("New...", self)
        self.addButton.clicked.connect(self.newUser)
        vbox.addWidget(self.addButton)
        user = self.users.query().get()
        self.details = UserDetails(user, self)
        layout.addWidget(self.details)
        self.setLayout(layout)

    def userSelected(self, index):
        self.details.setUser(self.users.getSelectedObject())

    def refresh(self):
        self.users.refresh()
        
    def newUser(self):
        pass

