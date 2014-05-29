'''
Created on May 23, 2014

@author: jan
'''

import threading
import gripe

logger = gripe.get_logger(__name__)

class LoggedCursor(object):
    def _interpolate(self, sql, args):
        return "%s <- %s" % (sql, args)
    
    def set_columns(self, columns, key_index):
        self._columns = columns
        self._key_index = key_index

    def execute(self, sql, args=None, **kwargs):
        if "columns" in kwargs:
            self._columns = kwargs["columns"]
        if "key_index" in kwargs:
            self._key_index = kwargs["key_index"]
        #logger.debug("sql: %s args %s", sql, args)
        logger.debug(self._interpolate(sql, args))
        try:
            super(LoggedCursor, self).execute(sql, args)
            logger.debug("Rowcount: %d", self.rowcount)
        except Exception, exc:
            logger.error("Cursor execute: %s %s", exc.__class__.__name__, exc)
            raise

    def columns(self):
        return self._columns

    def key_index(self):
        return self._key_index

    def single_row(self):
        try:
            return self.fetchone()
        finally:
            self.close()

    def single_row_bycolumns(self):
        values = self.single_row()
        return zip(self._columns, values) if values else None

    def singleton(self):
        return self.single_row()[0]

    #_close = close

    def _close(self):
        pass

    def close(self):
        if not self.closed:
            tx = Tx.get()
            if tx is not None:
                try:
                    tx.close_cursor(self)
                except:
                    logger.exception("Exception closing cursor")
            else:
                self._close()


class LoggedConnection(object):
    def commit(self):
        logger.debug("Commit")
        try:
            super(LoggedConnection, self).commit()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise

    def rollback(self):
        logger.warn("ROLLBACK")
        try:
            super(LoggedConnection, self).rollback()
        except Exception, exc:
            print exc.__class__.__name__, exc
            raise


class Tx(object):
    _init = False
    _tl = threading.local()
    _adapters = { "sqlite3": "gripe.sqlite.DbAdapter", "postgresql": "gripe.pgsql.DbAdapter" }

    def __init__(self, role, database, autocommit):
        if not Tx._init:
            Tx._init = True
            Tx._init_schema()
        self.cursors = []
        self.cache = {}
        self.active = True
        self.count = 0
        self.adapter = self.create_adapter(role, database, autocommit)
        self.conn = self.adapter.connect()
        Tx._tl.tx = self

    @classmethod
    def _init_schema(cls):
        config = gripe.Config.database
        if "adapters" in config:
            for a in config.adapters:
                cls._adapters[a] = config.adapters[a]
        cls._adapter_class = None
        for a in Tx._adapters:
            if a in config:
                cls._adapter_class = gripe.resolve(cls._adapters[a])
                c = config[a]
        if cls._adapter_class:
            cls._adapter_class.setup(c)
        
    @classmethod
    def begin(cls, role="user", database=None, autocommit=False):
        return cls._tl.tx \
            if hasattr(cls._tl, "tx") \
            else Tx(role, database, autocommit)

    @classmethod
    def get(cls):
        return cls._tl.tx if hasattr(cls._tl, "tx") else None
    
    def create_adapter(self, role, database, autocommit):
        self.adapter = self._adapter_class()
        self.adapter.initialize(role, database, autocommit)

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, exception_type, exception_value, trace):
        self.count -= 1
        if exception_type:
            logger.error("Exception in Tx block, Exception: %s %s %s",
                exception_type, exception_value, trace)
        if not self.count:
            try:
                self._end_tx()
            except Exception, exc:
                logger.error("Exception committing Tx, Exception: %s %s",
                    exc.__class__.__name__, exc)
        return False

    def get_cursor(self):
        ret = self.conn.cursor()
        self.cursors.append(ret)
        return ret

    def close_cursor(self, cur):
        self.cursors.remove(cur)
        cur._close()

    def _end_tx(self):
        try:
            try:
                for c in self.cursors:
                    c.close()
            finally:
                self.conn.commit()
                self.conn.close()
        finally:
            self.active = False
            self.cache = {}
            del self._tl.tx

    @staticmethod
    def get_from_cache(key):
        tx = Tx.get()
        return (tx.cache[key] if key in tx.cache else None) if tx else None

    @staticmethod
    def put_in_cache(obj):
        tx = Tx.get()
        if tx:
            key = obj.key() if hasattr(obj, "key") and callable(obj.key) else obj
            tx.cache[key] = obj

    @staticmethod
    def flush_cache():
        tx = Tx.get()
        if tx:
            del tx.cache
            tx.cache = {}

logger.info("Initialized module %s", __name__)

if __name__ == "__main__":
    with Tx.begin() as tx:
        cur = tx.get_cursor()
        cur.execute("CREATE TABLE grumble.a (foo TEXT)")
        cur.execute("INSERT INTO grumble.a (foo) VALUES ('jan')")
        cur.execute("SELECT * FROM grumble.a")
        print cur.singleton()
