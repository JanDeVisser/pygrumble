#
# Copyright (c) 2017 Jan de Visser (jan@sweattrails.com)
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

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal

import gripe
import gripe.db
import grizzle
import grumble.property
import sweattrails.qt.async.bg
import sweattrails.qt.mainwindow
import sweattrails.withings

logger = gripe.get_logger(__name__)


class NotAuthenticatedException(gripe.AuthException):
    def __str__(self):
        return "Not authenticated"


class SweatTrailsCore(object):
    refresh = pyqtSignal(QObject, name="refresh")

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
                self.authenticate(args.user, args.password, args.savecredentials)
            else:
                self.add_user(args.user, args.password, args.user, args.savecredentials)
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
        t = sweattrails.qt.async.bg.BackgroundThread.get_thread()
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
                self.refresh.emit(None)
                ret = True
        return ret

    # FIXME When creating a new user from within the app, should not confirm.
    # probably best to just add a new method for that.
    def add_user(self, uid, password, display_name, savecreds):
        um = self.user_manager()
        with gripe.db.Tx.begin():
            user = um.add(uid, password=password, display_name=display_name)
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
        job.jobError.connect(self.status_message)
        # sweattrails.qt.imports.BackgroundThread.add_backgroundjob(job)
        job.sync()

    def withings(self):
        t = sweattrails.qt.imports.BackgroundThread.get_thread()
        job = sweattrails.withings.WithingsJob()
        job.jobFinished.connect(self._refresh)
        t.addjob(job)
