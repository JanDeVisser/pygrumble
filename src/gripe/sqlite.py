'''
Created on May 23, 2014

@author: jan
'''

import os
import sqlite3
import shutil
import gripe
import gripe.db

logger = gripe.get_logger(__name__)

class Cursor(gripe.db.LoggedCursor, sqlite3.Cursor):
    pass

class Connection(gripe.db.LoggedConnection, sqlite3.Connection):
    def cursor(self):
        return super(Connection, self).cursor(Cursor)

class DbAdapter(object):
    
    @classmethod
    def setup(cls, sqlite_conf):
        cls.config = sqlite_conf
        cls._dbdir = sqlite_conf.dbdir if "dbdir" in sqlite_conf else "db"
        if isinstance(sqlite_conf.wipe, bool) and sqlite_conf.wipe:
            shutil.rmtree(os.path.join(gripe.root_dir(), cls._dbdir))
        gripe.mkdir(cls._dbdir)
            
    @classmethod
    def dbdir(cls):
        return os.path.join(gripe.root_dir(), cls._dbdir)

    def initialize(self, role, database, autocommit):
        self.role = role
        self.database = database
        self.autocommit = autocommit
        self.dbfile = os.path.join(self.dbdir(), "%s.db" % self.database)


    def connect(self):
        logger.debug("Opening database '%s'", self.database)
        conn = sqlite3.connect(self.dbfile, 
           isolation_level = None if self.autocommit else 'DEFERRED',
           factory = Connection)
        conn.autocommit = self.autocommit
        return conn
