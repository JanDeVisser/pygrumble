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

from PySide.QtCore import QCoreApplication
from PySide.QtCore import QThread
from PySide.QtCore import Signal

from PySide.QtGui import QCheckBox
from PySide.QtGui import QDialog
from PySide.QtGui import QDialogButtonBox
from PySide.QtGui import QTableWidget
from PySide.QtGui import QTableWidgetItem
from PySide.QtGui import QVBoxLayout

import gripe
import grumble.model
import grumble.property
import sweattrails.device.antfs
import sweattrails.device.exceptions
import sweattrails.device.fitparser

logger = gripe.get_logger(__name__)


class LoggingThread(QThread):
    logmessage = Signal(str)
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
        
    def log(self, msg, *args):
        self.logmessage.emit(msg.format(*args))
        
    def progress_init(self, msg, *args):
        self.progressInit.emit(msg.format(*args))
        
    def progress(self, percentage):
        self.progressUpdate.emit(percentage)
        
    def progress_end(self):
        self.progressEnd.emit()
        

class ImportedFITFile(grumble.model.Model):
    filename = grumble.property.StringProperty(is_key = True)
    status = grumble.property.BooleanProperty(default = False) 


class ImportThread(LoggingThread):
    importing = Signal(str)
    imported = Signal(str)
    importerror = Signal(str, str)
    queueEmpty = Signal()
    
    _singleton = None
    
    _parser_factories_by_ext = {
        "fit": sweattrails.device.fitparser.FITParser
    }
    
    _parser_factories = []
    
    def __init__(self):
        super(ImportThread, self).__init__()
        self._queue = Queue.Queue()
        if ("sweattrails" in gripe.Config and 
            "parsers" in gripe.Config["sweattrails"]):
            for i in gripe.Config["sweattrails"].parsers:
                cls = i["class"]
                cls = gripe.resolve(cls)
                ext = i.get("extension")
                if ext:
                    ImportThread._parser_factories_by_ext[ext] = cls
                else:
                    ImportThread._parser_factories.append(cls)
        
    def addfile(self, filename):
        self._queue.put(filename)
            
    def addfiles(self, filenames):
        for f in filenames:
            self.addfile(f)
            
    def run(self):
        self._stopped = False 
        while not self._stopped:
            self.scan_inbox()
            try:
                while True:
                    f = self._queue.get(True, 1)
                    self.import_file(f)
                    self._queue.task_done()
            except Queue.Empty:
                self.queueEmpty.emit()
        logger.debug("ImportThread finished")

    def scan_inbox(self):
        # We set up the paths every time since the user could have switched
        # since last time.
        #
        # FIXME - gripe should read from the session, which qt.app.SweatTrails 
        # should manage
        userdir = gripe.user_dir(QCoreApplication.instance().user.uid())
        self.inbox = os.path.join(userdir, "inbox")
        gripe.mkdir(self.inbox)
        self.queue =  os.path.join(userdir, "queue")
        gripe.mkdir(self.queue)
        self.done =  os.path.join(userdir, "done")
        gripe.mkdir(self.done)
        inboxfiles = gripe.listdir(self.inbox)
        for f in inboxfiles:
            gripe.rename(os.path.join(self.inbox, f), os.path.join(self.queue, f))
            self.addfile(os.path.join(gripe.root_dir(), self.queue, f))

    def import_file(self, filename):
        self.importing.emit(filename)
        try:
            f = os.path.basename(filename)
            (_, _, ext) = filename.rpartition(".")
            factory = ImportThread._parser_factories_by_ext.get(ext)
            if hasattr(factory, "create_parser"):
                parser = factory.create_parser(filename)
            else:
                parser = factory(filename)
            if not parser:
                for factory in ImportThread._parser_factories:
                    if hasattr(factory, "create_parser"):
                        parser = factory.createParser(filename)
                    if parser:
                        break
                if not parser:
                    logger.warning("No parser registered for %s", f)
                    return
            athlete = QCoreApplication.instance().user
            parser.setAthlete(athlete)
            parser.setLogger(self)
            with gripe.db.Tx.begin():
                q = ImportedFITFile.query('"filename" =', f, parent = athlete)
                fitfile = q.get()
                if not fitfile:
                    fitfile = ImportedFITFile(parent = athlete)
                    fitfile.filename = f
                    fitfile.status = False
                    fitfile.put()
            try:
                parser.parse()
            except sweattrails.device.exceptions.SessionExistsError as se:
                # Ignore if the file was generated by the ANT download.
                # Otherwise complain. 
                if "-st-antfs" not in filename:
                    raise
                
            # Move file to 'done' directory if it was in the queue before: 
            if os.path.basename(os.path.dirname(filename)) == "queue":
                gripe.rename(os.path.join(self.queue, f), os.path.join(self.done, f))
            # Set file to completed in the log:
            with gripe.db.Tx.begin():
                fitfile.status = True
                fitfile.put()
            self.imported.emit(filename)
        except sweattrails.device.exceptions.FileImportError as ie:
            logger.exception("Exception importing file")
            self.importerror.emit(filename, ie.message)

    @classmethod
    def get_thread(cls):
        if not cls._singleton:
            cls._singleton = ImportThread()
        return cls._singleton
    
    
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


class DownloadThread(LoggingThread, sweattrails.device.antfs.GripeConfigBridge):
    def __init__(self, manager):
        super(DownloadThread, self).__init__()
        self.manager = manager
        self.athlete = QCoreApplication.instance().user
        logger.debug("Creating bridge")
        self.garminbridge = sweattrails.device.antfs.GarminBridge(self)
        self.init_config()
        
    def run(self):
        logger.debug("DownloadThread.run")
        try:
            self.garminbridge.start()
        except:
            logger.exception("Exception in download thread")
        logger.debug("DownloadThread finished")


    #===========================================================================
    # C O N F I G  B R I D G E            
    #===========================================================================
    
    def exists(self, antfile):
        if antfile.get_date().year < 2000:
            return True
        with gripe.db.Tx.begin():
            q = ImportedFITFile.query(ancestor = self.athlete)
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
                                gripe.user_dir(self.athlete.uid()), 
                                "inbox",
                                self.get_filename(antfile))
            with open(path, "w") as fd:
                data.tofile(fd)
            f = self.get_filename(antfile)
            q = ImportedFITFile.query('"filename" =', f, parent = self.athlete)
            fitfile = q.get()
            if not fitfile:
                fitfile = ImportedFITFile(parent = self.athlete)
                fitfile.filename = f
            fitfile.status = False
            fitfile.put()

    def get_filename(self, antfile):
        return str.format("{0}-{1:02x}-{2}-st-antfs.fit",
                antfile.get_date().strftime("%Y-%m-%d_%H-%M-%S"),
                antfile.get_type(), antfile.get_size())

