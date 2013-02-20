__author__="jan"
__date__ ="$29-Jan-2013 11:00:39 AM$"

import logging
import psycopg2

class Cursor(psycopg2.extensions.cursor):
    def execute(self, sql, args=None):
        logging.debug(self.mogrify(sql, args))
        try:
            super(Cursor, self).execute(sql, args)
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

class Connection(psycopg2.extensions.connection):
    def cursor(self):
        return super(Connection, self).cursor(cursor_factory=Cursor)

    def commit(self):
        logging.debug("Commit")
        try:
            super(Connection, self).commit()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    def rollback(self):
        logging.warn("ROLLBACK")
        try:
            super(Connection, self).rollback()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    @classmethod
    def get(cls, dsn):
        logging.debug("Get pyscopg2 connection with DSN %s", dsn)
        return psycopg2.connect(dsn, connection_factory=Connection)
