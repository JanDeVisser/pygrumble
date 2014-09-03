# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import argparse
import sys

from PySide.QtCore import QCoreApplication
from PySide.QtCore import Signal

from PySide.QtGui import QApplication
from PySide.QtGui import QIcon
from PySide.QtGui import QPixmap
from PySide.QtGui import QSplashScreen

import gripe
import gripe.db
import grizzle
import grumble.property
import sweattrails.qt.imports
import sweattrails.qt.mainwindow

logger = gripe.get_logger("sweattrails.qt.app")

class SplashScreen(QSplashScreen):
    def __init__(self):
        super(SplashScreen, self).__init__(QPixmap("image/splash.png"))


class SweatTrailsCore(object):
    refresh = Signal()
    
    def init_config(self, user = None, password = None, savecreds = False):
        save = False
        self.user = self.user_id = None
        if "qtapp" not in gripe.Config:
            gripe.Config.qtapp = {}
        self.config = gripe.Config.qtapp
        if "settings" not in self.config:
            self.config["settings"] = {}
            save = True
        if save:
            self.config = gripe.Config.set("qtapp", self.config)
        save = False
        if user and password:
            self.authenticate(user, password, savecreds)
        else:
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
                
    def start(self, user = None, password = None, savecreds = False):
        self.init_config(user, password, savecreds)
        t = sweattrails.qt.imports.ImportThread.get_thread()
        t.logmessage.connect(self.log)
        t.progressInit.connect(self.reset_progress)
        t.progressUpdate.connect(self.progress)
        t.progressEnd.connect(self.progress_done)
        t.importing.connect(self.file_import_started)
        t.imported.connect(self.file_imported)
        t.importerror.connect(self.file_import_error)
        t.start()

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
            if user.authenticate(password = password):
                if savecreds:
                    self.config.settings["user"] = {
                        "user_id": uid,
                        "password": grumble.property.PasswordProperty.hash(password)
                    }
                    self.config = gripe.Config.set("qtapp", self.config)
                    logger.debug("Authenticated. Setting self.user")
                self.user_id = uid
                self.user = user
                ret = True
        return ret

    def is_authenticated(self):
        return self.user is not None

    def import_files(self, *filenames):
        t = sweattrails.qt.imports.ImportThread.get_thread()
        t.addfiles(filenames)

    def file_import_started(self, filename):
        self.log("Importing file {}", filename)
                
    def file_imported(self, filename):
        self.log("File {} successfully imported", filename)

    def file_import_error(self, filename, msg):
        self.log("ERROR importing file {}: {}", filename, msg)
        
    def download(self):
        t = sweattrails.qt.imports.DownloadThread()
        t.logmessage.connect(self.log)
        t.progressInit.connect(self.reset_progress)
        t.progressUpdate.connect(self.progress)
        t.progressEnd.connect(self.progress_done)
        if isinstance(app, SweatTrailsCmdLine):
            t.finished.connect(self.quit)
        t.start()


class SweatTrailsCmdLine(QCoreApplication, SweatTrailsCore):
    def __init__(self, argv):
        super(SweatTrailsCmdLine, self).__init__(argv)
        
    def file_import(self, filenames):            
        t = sweattrails.qt.imports.ImportThread.get_thread()
        t.importing.connect(self.setup_quit)
        t.addfiles(filenames)
        
    def setup_quit(self, filename):
        t = sweattrails.qt.imports.ImportThread.get_thread()
        t.queueEmpty.connect(self.quit)
        
    def log(self, msg, *args):
        print msg.format(*args)
        
    def reset_progress(self, msg, *args):
        self.curr_progress = 0
        sys.stdout.write((msg + " [").format(*args))
        sys.stdout.flush()
        
    def progress(self, new_progress):
        diff = new_progress/10 - self.curr_progress 
        sys.stderr.write("." * diff)
        sys.stdout.flush()
        self.curr_progress = new_progress/10
        
    def progress_done(self):
        sys.stdout.write("]\n")
        sys.stdout.flush()

        
class SweatTrails(QApplication, SweatTrailsCore):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)            
        icon = QPixmap("image/sweatdrops.png")
        self.setWindowIcon(QIcon(icon))
        self.splash = SplashScreen()

    def start(self, user, password, savecredentials):
        self.processEvents()
        self.splash.show()
        self.processEvents()
        super(SweatTrails, self).start(user, password, savecredentials)
        self.processEvents()
        with gripe.db.Tx.begin():
            self.mainwindow = sweattrails.qt.mainwindow.STMainWindow()
        self.mainwindow.show()
        self.splash.finish(self.mainwindow)
        self.splash = None

    def log(self, msg, *args):
        self.mainwindow.log(msg, *args)

    def reset_progress(self, msg, *args):
        self.mainwindow.reset_progress(msg, *args)
        
    def progress(self, percentage):
        self.mainwindow.progress(percentage)
        
    def progress_done(self):
        self.mainwindow.progress_done()
        
#===============================================================================
# Parse command line
#===============================================================================

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--download", action="store_true",
                    help="download new activities from your Garmin device over ANT+")
parser.add_argument("-i", "--import", dest="imp", type=str, nargs="+",
                    help="import the given file")
parser.add_argument("-u", "--user", type=str, 
    help="""Username to log in as. Note that this overrides a possibly stored username""")
parser.add_argument("-P", "--password", type=str, 
    help="""Password to use when logging in. Only used when -u/--user is specified as well. 
Note that this overrides a possibly stored password.""")
parser.add_argument("-S", "--savecredentials", action="store_true")
parser.set_defaults(savecredentials=False, download=False)

args = parser.parse_args()
if args.user:
    assert args.password, "--password option requires --user option"
if args.savecredentials:
    assert args.user and args.password, \
        "--savecredentials option requires --user and --password option"


#===============================================================================
# Build Application objects based on command line:
#===============================================================================

appcls = SweatTrailsCmdLine if args.imp or args.download else SweatTrails
app = appcls(sys.argv)
app.start(args.user, args.password, args.savecredentials)

if args.imp:
    app.file_import(args.imp)

if args.download:
    app.download()

app.exec_()
