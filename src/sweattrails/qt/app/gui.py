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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen

import gripe
import gripe.db
import sweattrails.qt.app.core
import sweattrails.qt.imports
import sweattrails.qt.mainwindow
import sweattrails.withings

logger = gripe.get_logger(__name__)


class SplashScreen(QSplashScreen):
    def __init__(self):
        super(SplashScreen, self).__init__(QPixmap("image/splash.png"))


class SweatTrails(QApplication, sweattrails.qt.app.core.SweatTrailsCore):
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
            self.mainwindow.setSession(args.session)
        if args.tab:
            self.mainwindow.setTab(args.tab)

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
