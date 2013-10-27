__author__="jan"
__date__ ="$29-Jan-2013 11:00:39 AM$"

import sys
import threading
import psycopg2
import gripe

logger = gripe.get_logger(__name__)

class Cursor(psycopg2.extensions.cursor):
    def set_columns(self, columns, key_index):
        self._columns = columns
        self._key_index = key_index

    def execute(self, sql, args=None, **kwargs):
        if "columns" in kwargs:
            self._columns = kwargs["columns"]
        if "key_index" in kwargs:
            self._key_index = kwargs["key_index"]
        logger.debug("sql: %s args %s", sql, args)
        logger.debug(self.mogrify(sql, args))
        try:
            super(Cursor, self).execute(sql, args)
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

class Tx(object):
    _init = False
    _tl = threading.local()

    def __init__(self, role, database, autocommit):
        if not Tx._init:
            Tx._init = True
            Tx._init_schema()
        self.role = role
        self.database = database
        self.autocommit = autocommit
        self.cursors = []
        self.cache = {}
        self.active = True
        self.count = 0
        self._connect()
        Tx._tl.tx = self

    @classmethod
    def _init_schema(cls):
        config = gripe.Config.database
        assert config.postgresql, """
            Config: conf/database.json is missing postgresql section"""
        pgsql_conf = config.postgresql
        assert pgsql_conf.user, """
            Config: No user role in postgresql section of
            conf/database.json"""
        pgsql_user = pgsql_conf.user
        assert pgsql_conf.admin, """
            Config: No admin role in postgresql section of
            conf/database.json"""
        pgsql_admin = pgsql_conf.admin
        assert pgsql_user.user_id and pgsql_user.password, """
            Config: user role is missing user_id or password in postgresql
            section of conf/database.json"""
        assert pgsql_admin.user_id and pgsql_admin.password, """
            Config: admin role is missing user_id or password in postgresql
            section of conf/database.json"""

        if pgsql_conf.database:
            database = pgsql_conf.database
            if database != 'postgres':
                # We're assuming the postgres database exists and should
                # never be wiped:
                with Tx.begin("admin", "postgres", True) as tx:
                    cur = tx.get_cursor()
                    create_db = False
                    if isinstance(pgsql_conf.wipe_database, bool) \
                            and pgsql_conf.wipe_database:
                        cur.execute('DROP DATABASE IF EXISTS "%s"' %
                            (database,))
                        create_db = True
                    else:
                        cur.execute("SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname = %s", (database,))
                        create_db = (cur.fetchone()[0] == 0)
                    if create_db:
                        cur.execute('CREATE DATABASE "%s"' % (database,))

        if pgsql_conf.schema:
            with Tx.begin("admin") as tx:
                cur = tx.get_cursor()
                create_schema = False
                schema = pgsql_conf.schema
                if isinstance(pgsql_conf.wipe_schema, bool) \
                        and pgsql_conf.wipe_schema:
                    cur.execute('DROP SCHEMA IF EXISTS "%s" CASCADE' % schema)
                    create_schema = True
                else:
                    cur.execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s", (schema,))
                    create_schema = (cur.fetchone()[0] == 0)
                if create_schema:
                    cur.execute(
                        'CREATE SCHEMA "%s" AUTHORIZATION %s' %
                        (schema, pgsql_conf["user"]["user_id"]))

    def _connect(self):
        config = gripe.Config.database
        pgsql_conf = config.postgresql
        dsn = "user=%s password=%s" % (
            getattr(pgsql_conf, self.role).user_id,
            getattr(pgsql_conf, self.role).password)
        if not self.database:
            self.database = pgsql_conf.database
        if not self.database:
            self.database = "postgres" \
                if self.role == "admin" \
                else getattr(pgsql_conf, self.role).user_id
        dsn += " dbname=%s" % self.database
        if pgsql_conf.host:
            dsn += " host=%s" % pgsql_conf.host
        logger.debug("Connecting with role '%s' autocommit = %s",
            self.role, self.autocommit)
        self.conn = Connection.get(dsn)
        self.conn.autocommit = self.autocommit

    @classmethod
    def begin(cls, role="user", database=None, autocommit=False):
        return cls._tl.tx \
            if hasattr(cls._tl, "tx") \
            else Tx(role, database, autocommit)

    @classmethod
    def get(cls):
        return cls._tl.tx if hasattr(cls._tl, "tx") else None

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

