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

import argparse
import sys
import threading
import traceback

from PySide.QtCore import QCoreApplication
from PySide.QtCore import QObject
from PySide.QtCore import Signal

from PySide.QtGui import QApplication
from PySide.QtGui import QIcon
from PySide.QtGui import QPixmap
from PySide.QtGui import QSplashScreen

sys.path.append(".")

import gripe
import gripe.db
import grizzle
import grumble.property
import sweattrails.qt.imports
import sweattrails.qt.mainwindow
import sweattrails.withings

logger = gripe.get_logger(__name__)

class NotAuthenticatedException(gripe.AuthException):
    def __str__(self):
        return "Not authenticated"

class SplashScreen(QSplashScreen):
    def __init__(self):
        super(SplashScreen, self).__init__(QPixmap("image/splash.png"))


class SweatTrailsCore(object):
    refresh = Signal(QObject)

    def init_config(self, args):
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
        if args.user and args.password:
            if QCoreApplication.instance().has_users():
                self.authenticate(args.user, args.password, args.savecreds)
            else:
                self.add_user(args.user, args.password, args.user, args.savecreds)
        else:
            if "user" in self.config.settings:
                user_settings = self.config.settings.user
                uid = user_settings.user_id if "user_id" in user_settings else None
                password = user_settings.password if "password" in user_settings else None
                logger.debug("Auto-login uid %s", uid)
                if not uid or not self.authenticate(uid, password, False):
                    del self.config.settings["user"]
                    save = True
        if save:
            self.config = gripe.Config.set("qtapp", self.config)

    def start(self, args):
        self.init_config(args)
        t = sweattrails.qt.imports.BackgroundThread.get_thread()
        t.statusMessage.connect(self.status_message)
        t.progressInit.connect(self.progress_init)
        t.progressUpdate.connect(self.progress)
        t.progressEnd.connect(self.progress_done)
        t.jobStarted.connect(self.status_message)
        t.jobFinished.connect(self.status_message)
        t.jobError.connect(self.status_message)
        t.start()

    def user_manager(self):
        if not hasattr(self, "_user_manager"):
            self._user_manager = grizzle.UserManager()
        return self._user_manager

    def has_users(self):
        mgr = self.user_manager()
        return mgr.has_users()

    def authenticate(self, uid, password, savecreds = False):
        logger.debug("Authenticating uid %s", uid)
        self.user = None
        self.user_id = None
        um = self.user_manager()
        ret = False
        with gripe.db.Tx.begin():
            user = um.get(uid)
            if user and user.authenticate(password = password):
                if savecreds:
                    self.config.settings["user"] = {
                        "user_id": uid,
                        "password": grumble.property.PasswordProperty.hash(password)
                    }
                    self.config = gripe.Config.set("qtapp", self.config)
                    logger.debug("Authenticated. Setting self.user")
                self.user_id = uid
                self.user = user
                self.refresh.emit()
                ret = True
        return ret

    # FIXME When creating a new user from within the app, should not confirm.
    # probably best to just add a new method for that.
    def add_user(self, uid, password, display_name, savecreds):
        um = self.user_manager()
        with gripe.db.Tx.begin():
            user = um.add(uid, password = password, display_name = display_name)
            user.confirm()
        return self.authenticate(uid, password, savecreds)

    def is_authenticated(self):
        return self.user is not None

    def import_files(self, *filenames):
        t = sweattrails.qt.imports.BackgroundThread.get_thread()
        for f in filenames:
            job = sweattrails.qt.imports.ImportFile(f)
            job.jobFinished.connect(self._refresh)
            t.addjob(job)

    def _refresh(self, job):
        self.refresh.emit(job)

    def download(self):
        job = sweattrails.qt.imports.DownloadJob(self.getDownloadManager())
        job.jobFinished.connect(self._refresh)
        # sweattrails.qt.imports.BackgroundThread.add_backgroundjob(job)
        job.sync(threading.currentThread())

    def withings(self):
        t = sweattrails.qt.imports.BackgroundThread.get_thread()
        job = sweattrails.withings.WithingsJob()
        job.jobFinished.connect(self._refresh)
        t.addjob(job)


class SweatTrailsCmdLine(QCoreApplication, SweatTrailsCore):
    def __init__(self, argv):
        super(SweatTrailsCmdLine, self).__init__(argv)

    def start(self, args):
        super(SweatTrailsCmdLine, self).start(args)
        if not self.is_authenticated():
            raise NotAuthenticatedException()

    def file_import(self, filenames):
        self.import_files(*filenames)

    def setup_quit(self, filename):
        t = sweattrails.qt.imports.BackgroundThread.get_thread()
        t.queueEmpty.connect(self.quit)

    def after_download(self):
        self.quit()

    def status_message(self, msg, *args):
        print msg.format(*args)

    def progress_init(self, msg, *args):
        self.curr_progress = 0
        sys.stdout.write((msg + " [").format(*args))
        sys.stdout.flush()

    def progress(self, new_progress):
        diff = new_progress / 10 - self.curr_progress
        sys.stderr.write("." * diff)
        sys.stdout.flush()
        self.curr_progress = new_progress / 10

    def progress_done(self):
        sys.stdout.write("]\n")
        sys.stdout.flush()

    def getDownloadManager(self):
        return self

    def selectActivities(self, antfiles):
        return antfiles


class SweatTrails(QApplication, SweatTrailsCore):
    def __init__(self, argv):
        super(SweatTrails, self).__init__(argv)
        icon = QPixmap("image/sweatdrops.png")
        self.setWindowIcon(QIcon(icon))
        self.splash = SplashScreen()

    def start(self, args):
        super(SweatTrails, self).start(args)
        self.splash.show()
        self.processEvents()
        with gripe.db.Tx.begin():
            self.mainwindow = sweattrails.qt.mainwindow.STMainWindow()
        self.splash.finish(self.mainwindow)
        self.splash = None
        self.mainwindow.show()
        if args.session:
            app.mainwindow.setSession(args.session)
        if args.tab:
            app.mainwindow.setTab(args.tab)

    def status_message(self, msg, *args):
        self.mainwindow.status_message(msg, *args)

    def progress_init(self, msg, *args):
        self.mainwindow.progress_init(msg, *args)

    def progress(self, percentage):
        self.mainwindow.progress(percentage)

    def progress_done(self):
        self.mainwindow.progress_done()

    def before_download(self, thread):
        # Disable menu items:
        #  * Download
        #  * User switch
        #  * Exit
        pass

    def after_download(self):
        # Reset menu items
        pass

    def getDownloadManager(self):
        if not hasattr(self, "_downloadManager"):
            self._downloadManager = sweattrails.qt.imports.SelectActivities()
        return self._downloadManager


#===============================================================================
# Parse command line
#===============================================================================

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--download", action = "store_true",
                    help = "Download new activities from your Garmin device over ANT+")
parser.add_argument("-i", "--import", dest = "imp", type = str, nargs = "+",
                    help = "Import the given file")
parser.add_argument("-W", "--withings", action = "store_true",
                    help = "Download Withings data")
parser.add_argument("-u", "--user", type = str,
    help = """Username to log in as. Note that this overrides a possibly stored username""")
parser.add_argument("-P", "--password", type = str,
    help = """Password to use when logging in. Only used when -u/--user is specified as well.
Note that this overrides a possibly stored password.""")
parser.add_argument("-S", "--savecredentials", action = "store_true")
parser.add_argument("-s", "--session", type = str,
                    help = """Open the session with the given ID""")
parser.add_argument("-t", "--tab", type = int,
                    help = """Focus on the tab with the given index""")
parser.set_defaults(savecredentials = False, download = False)

args = parser.parse_args()
if args.user:
    assert args.password, "--password option requires --user option"
if args.savecredentials:
    assert args.user and args.password, \
        "--savecredentials option requires --user and --password option"


#===============================================================================
# Build Application objects based on command line:
#===============================================================================

appcls = SweatTrailsCmdLine \
    if args.imp or args.download or args.withings \
    else SweatTrails
app = appcls(sys.argv)
app.start(args)

try:
    if args.imp:
        app.file_import(args.imp)

    if args.download:
        app.download()

    if args.withings:
        app.withings()


except Exception as e:
    print(e)
    traceback.print_exc()

app.exec_()
