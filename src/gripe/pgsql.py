__author__="jan"
__date__ ="$29-Jan-2013 11:00:39 AM$"

import logging
import psycopg2
import gripe

logger = gripe.get_logger(__name__)

class Cursor(psycopg2.extensions.cursor):
    def set_columns(self, columns, key_index):
        self._columns = columns
        self._key_index = key_index

    def execute(self, sql, args=None):
        logger.debug(self.mogrify(sql, args))
        try:
            super(Cursor, self).execute(sql, args)
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    def columns(self):
        return self._columns

    def key_index(self):
        return self._key_index

    def single_row(self):
        try:
            return self._cursor.fetchone()
        finally:
            self.close()

    def single_row_bycolumns(self):
        values = self.single_row()
        return zip(self._columns, values) if values else None

    def singleton(self):
        return self.single_row()[0]

    def _close(self):
        return super(psycopg2.extensions.cursor, self).close()

    def close(self):
        if not self.closed:
            tx = Tx.get()
            if tx is not None:
                try:
                    tx.close_cursor(self._cursor)
                except:
                    logger.error("Exception closing cursor")
            else:
                self._close()

class Connection(psycopg2.extensions.connection):
    def cursor(self):
        return super(Connection, self).cursor(cursor_factory=Cursor)

    def commit(self):
        logger.debug("Commit")
        try:
            super(Connection, self).commit()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    def rollback(self):
        logger.warn("ROLLBACK")
        try:
            super(Connection, self).rollback()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    @classmethod
    def get(cls, dsn):
        logger.debug("Get pyscopg2 connection with DSN %s", dsn)
        return psycopg2.connect(dsn, connection_factory=Connection)

logger.info("Initialized module %s", __name__)
