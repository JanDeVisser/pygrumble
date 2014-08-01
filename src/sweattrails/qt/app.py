# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import sys

from PySide.QtGui import QApplication
from PySide.QtGui import QPixmap
from PySide.QtGui import QSplashScreen

import gripe
import gripe.db
import grizzle
import grumble.property
import sweattrails.qt.mainwindow

logger = gripe.get_logger("qt")

class SplashScreen(QSplashScreen):
    def __init__(self):
        super(SplashScreen, self).__init__(QPixmap("image/splash.png"))


class SweatTrails(QApplication):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)
        self.splash = SplashScreen()
        
    def start(self):
        self.processEvents()
        self.splash.show()
        self.processEvents()
        self.init_config()
        self.processEvents()
        with gripe.db.Tx.begin():
            self.mainwindow = sweattrails.qt.mainwindow.STMainWindow()
        self.mainwindow.show()
        self.splash.finish(self.mainwindow)
        self.splash = None

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
            logger.debug("Auto-login uid %s", uid)
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
        logger.debug("Authenticating uid %s", uid)
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
                    logger.debug("Authenticated. Setting self.user")
                self.user_id = uid
                self.user = user
                ret = True
        return ret

    def is_authenticated(self):
        return self.user is not None

app = SweatTrails(sys.argv)
app.start()

app.exec_()
