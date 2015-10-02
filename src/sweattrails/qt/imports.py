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

import os.path
import Queue
import threading
import traceback

from PySide.QtCore import QCoreApplication
from PySide.QtCore import QObject
from PySide.QtCore import QThread
from PySide.QtCore import Signal

from PySide.QtGui import QCheckBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QTableWidget
from PySide.QtGui import QTableWidgetItem
from PySide.QtGui import QVBoxLayout

import gripe
import gripe.db
import grumble.model
import grumble.property
import sweattrails.device.antfs
import sweattrails.device.exceptions
import sweattrails.device.fitparser
import sweattrails.device.tcxparser

logger = gripe.get_logger(__name__)

class LoggingThread(QThread):
    statusMessage = Signal(str)
    progressInit = Signal(str)
    progressUpdate = Signal(int)
    progressEnd = Signal()
    
    def __init__(self, *args):
        super(LoggingThread, self).__init__(*args)
        QCoreApplication.instance().aboutToQuit.connect(self.quit)
        
    def quit(self):
        self.stop()
        self.wait()
        
    def stop(self):
        self._stopped = True
        
    def status_message(self, msg, *args):
        self.statusMessage.emit(msg.format(*args))
        
    def progress_init(self, msg, *args):
        self.progressInit.emit(msg.format(*args))
        
    def progress(self, percentage):
        self.progressUpdate.emit(percentage)
        
    def progress_end(self):
        self.progressEnd.emit()
        

class ImportedFITFile(grumble.model.Model):
    filename = grumble.property.StringProperty(is_key = True)
    status = grumble.property.BooleanProperty(default = False)


class Job(QObject):
    jobStarted = Signal(QObject)
    jobFinished = Signal(QObject)
    jobError = Signal(QObject)
    err = Signal(Exception)
    
    def __init__(self):
        super(Job, self).__init__()
        self.user = QCoreApplication.instance().user

    def sync(self):
        self._handle(None)

    def _handle(self, thread):
        self.jobStarted.emit(self)
        self.thread = thread
        logger.debug("Handling job %s", self)
        try:
            with gripe.db.Tx.begin():
                self.handle()
            self.jobFinished.emit(self)
        except Exception as e:
            self.jobError.emit(e)

    def started(self, msg):
        if self.thread:
            self.thread.jobStarted.emit(msg)

    def finished(self, msg):
        if self.thread:
            self.thread.jobFinished.emit(msg)

    def error(self, msg, error):
        if self.thread:
            self.thread.jobError.emit("ERROR %s" % msg, error)

    def status_message(self, msg, *args):
        if self.thread:
            self.thread.status_message(msg, *args)
        
    def progress_init(self, msg, *args):
        if self.thread:
            self.thread.progress_init(msg, *args)
        
    def progress(self, percentage):
        if self.thread:
            self.thread.progress(percentage)
        
    def progress_end(self):
        if self.thread:
            self.thread.progress_end()
        

class ImportFile(Job):
    _parser_factories_by_ext = {
        "fit": sweattrails.device.fitparser.FITParser,
        "tcx": sweattrails.device.tcxparser.TCXParser
    }
    
    _parser_factories = []

    if ("sweattrails" in gripe.Config.app and 
        "parsers" in gripe.Config.app.sweattrails):
        for i in gripe.Config.app.sweattrails.parsers:
            cls = i["class"]
            cls = gripe.resolve(cls)
            ext = i.get("extension")
            if ext:
                _parser_factories_by_ext[ext] = cls
            else:
                _parser_factories.append(cls)
    
    def __init__(self, filename):
        super(ImportFile, self).__init__()
        self.filename = filename
        userdir = gripe.user_dir(self.user.uid())
        self.inbox = os.path.join(userdir, "inbox")
        self.queue = os.path.join(userdir, "queue")
        self.done = os.path.join(userdir, "done")

    def get_parser(self):
        f = os.path.basename(self.filename)
        parser = None
        
        (_, _, ext) = f.rpartition(".")
        if ext:
            ext = ext.lower()
        factory = ImportFile._parser_factories_by_ext.get(ext)
        if factory:
            if hasattr(factory, "create_parser"):
                parser = factory.create_parser(self.filename)
            else:
                parser = factory(self.filename)
        if not parser:
            for factory in ImportFile._parser_factories:
                if hasattr(factory, "create_parser"):
                    parser = factory.create_parser(self.filename)
                else:
                    parser = factory(self.filename)
                if parser:
                    break
        return parser

    def handle(self):
        logger.debug("ImportFile: Importing file %s", self.filename)
        self.started("Importing file %s" % self.filename)
        try:
            f = os.path.basename(self.filename)
            parser = self.get_parser()
            if not parser:
                logger.warning("No parser registered for %s", f)
                return
            parser.set_athlete(self.user)
            parser.set_logger(self.thread)
            q = ImportedFITFile.query('"filename" =', f, parent = self.user)
            fitfile = q.get()
            if not fitfile:
                fitfile = ImportedFITFile(parent = self.user)
                fitfile.filename = f
                fitfile.status = False
                fitfile.put()
            try:
                parser.parse()
            except sweattrails.device.exceptions.SessionExistsError:
                # Ignore if the file was generated by the ANT download.
                # Otherwise complain. 
                if "-st-antfs" not in self.filename:
                    raise
                
            # Move file to 'done' directory if it was in the queue before: 
            if os.path.basename(os.path.dirname(self.filename)) == "queue":
                gripe.rename(os.path.join(self.queue, f), os.path.join(self.done, f))
                
            # Set file to completed in the log:
            with gripe.db.Tx.begin():
                fitfile.status = True
                fitfile.put()
                
            self.finished("File %s successfully imported" % self.filename)
        except sweattrails.device.exceptions.FileImportError as ie:
            logger.exception("Exception importing file")
            self.error("Importing file %s" % self.filename, ie.message)
            raise


class ThreadPlugin(object):
    def __init__(self, thread):
        self.thread = thread
                               
    def addjob(self, job):
        self.thread.addjob(job)
                               
    def run(self):
        pass


class ScanInbox(ThreadPlugin):
    def __init__(self, thread):
        super(ScanInbox, self).__init__(thread)
        self.user = None
        self._setuser()
        
    def addfile(self, filename):
        self.addjob(ImportFile(filename))
            
    def addfiles(self, filenames):
        for f in filenames:
            self.addfile(f)
            
    def _setuser(self):
        # FIXME - gripe should read from the session, which qt.app.SweatTrails 
        # should manage
        user = QCoreApplication.instance().user
        if user != self.user:
            self.user = user
            userdir = gripe.user_dir(user.uid())
            self.inbox = os.path.join(userdir, "inbox")
            gripe.mkdir(self.inbox)
            self.queue =  os.path.join(userdir, "queue")
            gripe.mkdir(self.queue)
            done =  os.path.join(userdir, "done")
            gripe.mkdir(done)
            
    def run(self):
        # We set up the paths every time since the user could have switched
        # since last time.
        self._setuser()
        if self.user:
            inboxfiles = gripe.listdir(self.inbox)
            for f in inboxfiles:
                logger.debug("ScanInbox: Found file %s", f)
                gripe.rename(os.path.join(self.inbox, f), os.path.join(self.queue, f))
                self.addfile(os.path.join(gripe.root_dir(), self.queue, f))


class BackgroundThread(LoggingThread):
    jobStarted = Signal(str)
    jobFinished = Signal(str)
    jobError = Signal(str, str)
    queueEmpty = Signal()
    
    _singleton = None
    _plugins = []
    
    def __init__(self):
        super(BackgroundThread, self).__init__()
        self._queue = Queue.Queue()
        if ("sweattrails" in gripe.Config.app and 
            "background" in gripe.Config.app.sweattrails and
            "plugins" in gripe.Config.app.sweattrails.background):
            for plugin in gripe.Config.app.sweattrails.background.plugins:
                logger.debug("Initializing backgroung plugin '%s'", plugin)
                plugin = gripe.resolve(plugin)
                self._plugins.append(plugin(self))
        
    def addjob(self, job):
        job.thread = self
        self._queue.put(job)
            
    def run(self):
        self._stopped = False 
        while not self._stopped:
            for plugin in self._plugins:
                plugin.run()
            try:
                while True:
                    job = self._queue.get(True, 1)
                    try:
                        job._handle(self)
                    except Exception:
                        traceback.print_exc()
                    self._queue.task_done()
            except Queue.Empty:
                self.queueEmpty.emit()
        logger.debug("BackgroundThread finished")

    @classmethod
    def get_thread(cls):
        if not cls._singleton:
            cls._singleton = BackgroundThread()
        return cls._singleton

    @classmethod
    def add_backgroundjob(cls, job):
        t = cls.get_thread()
        t.addjob(job)


class SelectActivities(QDialog):
    select = Signal()

    def __init__(self, parent = None):
        super(SelectActivities, self).__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(parent)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["", "Date", "Size"])
        self.table.setColumnWidth(0, 25)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(3, 80)
        layout.addWidget(self.table)
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.select.connect(self._select)
        layout.addWidget(self.buttonbox)
        self.setMinimumSize(320, 200)
        
    def selectActivities(self, antfiles):
        logger.debug("SelectActivities.selectActivities")
        self.antfiles = antfiles
        self.lock = threading.Condition()
        self.lock.acquire()
        self.select.emit()
        logger.debug("SelectActivities.selectActivities: signal emitted")
        self.lock.wait()
        self.lock.release()
        logger.debug("SelectActivities.selectActivities: returning %s selected activities", len(self._selected))
        return self._selected

    def _select(self):
        logger.debug("SelectActivities._select")
        self.table.clear()
        self.table.setRowCount(len(self.antfiles))
        for row in range(len(self.antfiles)):
            f = self.antfiles[row]
            self.table.setCellWidget(row, 0, QCheckBox(self))
            self.table.setItem(row, 1,
                QTableWidgetItem(f.get_date().strftime("%d %b %Y %H:%M")))
            self.table.setItem(row, 2,
                QTableWidgetItem("{:d}".format(f.get_size())))
        result = self.exec_()
        self._selected = []
        if result == QDialog.Accepted:
            for i in range(len(self.antfiles)):
                f = self.antfiles[i]
                cb = self.table.cellWidget(i, 0)
                if cb.isChecked():
                    self._selected.append(f)
        self.lock.acquire()
        logger.debug("SelectActivities._select: lock acquired")
        self.lock.notify()
        self.lock.release()


class DownloadJob(Job):
    def __init__(self, manager):
        super(DownloadJob, self).__init__()
        self.manager = manager

    def handle(self):
        logger.debug("Garmin download")
        self.started("Downloading from Garmin")
        with sweattrails.device.antfs.GarminBridge.acquire(self) as gb:
            try:
                gb.on_transport()
                logger.debug("Garmin download finished")
                self.finished("Garmin download finished")
            except sweattrails.device.exceptions.FileImportError as ie:
                logger.exception("Exception in download job")
                self.error("Garmin download", ie.message)
                raise

    #===========================================================================
    # C O N F I G  B R I D G E            
    #===========================================================================
    
    def exists(self, antfile):
        if antfile.get_date().year < 2000:
            return True
        with gripe.db.Tx.begin():
            q = ImportedFITFile.query(ancestor = self.user)
            q.add_filter("filename", "=", self.get_filename(antfile))
            q.add_filter("status", "=", True)
            return q.get() is not None
        
    def select(self, antfiles):
        logger.debug("DownloadThread.select: %s files available", len(antfiles))
        selected = self.manager.selectActivities(antfiles)
        logger.debug("DownloadThread.select: %s files selected", len(selected))
        return selected

    def process(self, antfile, data):
        with gripe.db.Tx.begin():
            path = os.path.join(gripe.root_dir(), 
                                gripe.user_dir(self.user.uid()), 
                                "inbox",
                                self.get_filename(antfile))
            with open(path, "w") as fd:
                data.tofile(fd)
            f = self.get_filename(antfile)
            q = ImportedFITFile.query('"filename" =', f, parent = self.user)
            fitfile = q.get()
            if not fitfile:
                fitfile = ImportedFITFile(parent = self.user)
                fitfile.filename = f
            fitfile.status = False
            fitfile.put()

    def get_filename(self, antfile):
        return str.format("{0}-{1:02x}-{2}-st-antfs.fit",
                antfile.get_date().strftime("%Y-%m-%d_%H-%M-%S"),
                antfile.get_type(), antfile.get_size())

