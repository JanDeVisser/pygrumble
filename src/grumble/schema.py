# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$17-Sep-2013 11:47:03 AM$"

import gripe.db

logger = gripe.get_logger(__name__)

class ColumnDefinition(object):
    def __init__(self, name, data_type, required, defval, indexed):
        self.name = name
        self.data_type = data_type
        self.required = required
        self.defval = defval
        self.indexed = indexed
        self.is_key = False
        self.scoped = False

class DbAdapter(object):
    def __init__(self, modelmanager):
        self._mm = modelmanager
        
    def __getattr__(self, name):
        return getattr(self._mm, name)

        
class Sqlite3Adapter(DbAdapter):
    def __init__(self, modelmanager):
        super(Sqlite3Adapter, self).__init__(modelmanager)
        self._mm.tableprefix = ""

    def table_exists(self, cur):
        sql = "SELECT name FROM sqlite_master WHERE name = %s"
        v = [ self.table ]
        cur.execute(sql, v)
        return cur.fetchone() is not None
    
    def __str__(self):
        return self._mm.__str__()
    
    def update_table(self, cur, table_existed = False):
        # FIXME - Doesn't really work.
        if table_existed and self._recon != "all":
            logger.info("%s: reconcile() _recon is '%s' and table existed. Leaving table alone", self, self._recon)
            return
        if False:
            for c in self.columns:
                vars = []
                sql = 'ALTER TABLE %s ADD COLUMN "%s" %s' % (self.tablename, c.name, c.data_type)
                if c.required:
                    sql += " NOT NULL"
                if c.defval:
                    sql += " DEFAULT %s"
                    vars.append(c.defval)
                if c.is_key and not c.scoped:
                    sql += " PRIMARY KEY"
                cur.execute(sql, vars)
                if c.indexed and not c.is_key:
                    cur.execute('CREATE INDEX "%s_%s" ON %s ( "%s" )' % (self.table, c.name, self.tablename, c.name))
                if c.is_key and c.scoped:
                    cur.execute('CREATE UNIQUE INDEX "%s_%s" ON %s ( "_parent", "%s" )' % (self.table, c.name, self.tablename, c.name))


class PostgresqlAdapter(DbAdapter):
    def __init__(self, modelmanager):
        super(PostgresqlAdapter, self).__init__(modelmanager)
        self._mm.schema = gripe.Config.database.postgresql.schema
        self._mm.tableprefix = '"%s".' % gripe.Config.database.postgresql.schema \
            if gripe.Config.database.postgresql.schema else ""

    def table_exists(self, cur):
        sql = "SELECT table_name FROM information_schema.tables WHERE table_name = %s"
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        return cur.fetchone() is not None

    def update_table(self, cur, table_existed = False):
        if table_existed and self._recon != "all":
            logger.info("%s: reconcile() _recon is '%s' and table existed. Leaving table alone", self, self._recon)
            return
        sql = "SELECT column_name, column_default, is_nullable, data_type FROM information_schema.columns WHERE table_name = %s"
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        coldescs = []
        for coldesc in cur:
            coldescs.append(coldesc)
        for c in self.columns:
            c._exists = False
        for (colname, defval, is_nullable, data_type) in coldescs:
            column = None
            for c in self.columns:
                if c.name == colname:
                    column = c
                    break
            if column:
                column._exists = True
                if data_type.lower() != column.data_type.lower() and self._recon == "all":
                    logger.info("Data type change: %s.%s %s -> %s", \
                                    self.tablename, colname, data_type.lower(), \
                                    column.data_type.lower())
                    cur.execute('ALTER TABLE %s DROP COLUMN "%s"' % (self.tablename, colname))
                    column._exists = False
                else:
                    c._exists = True
                    alter = ""
                    vars = []
                    if column.required != (is_nullable == 'NO'):
                        logger.info("NULL change: %s.%s required %s -> is_nullable %s", \
                                        self.tablename, colname, \
                                        column.required, is_nullable)
                        alter = " SET NOT NULL" if column.required else " DROP NOT NULL"
                    if column.defval != defval:
                        alter += " SET DEFAULT %s"
                        vars.append(column.defval)
                    if alter != "":
                        cur.execute('ALTER TABLE %s ALTER COLUMN "%s" %s' % \
                                        (self.tablename, colname, alter), vars)
            else:
                # Column not found. Drop it:
                cur.execute('ALTER TABLE %s DROP COLUMN "%s"' % (self.tablename, colname))
        for c in filter(lambda c: not c._exists, self.columns):
            vars = []
            sql = 'ALTER TABLE %s ADD COLUMN "%s" %s' % (self.tablename, c.name, c.data_type)
            if c.required:
                sql += " NOT NULL"
            if c.defval:
                sql += " DEFAULT %s"
                vars.append(c.defval)
            if c.is_key and not c.scoped:
                sql += " PRIMARY KEY"
            cur.execute(sql, vars)
            if c.indexed and not c.is_key:
                cur.execute('CREATE INDEX "%s_%s" ON %s ( "%s" )' % (self.table, c.name, self.tablename, c.name))
            if c.is_key and c.scoped:
                cur.execute('CREATE UNIQUE INDEX "%s_%s" ON %s ( "_parent", "%s" )' % (self.table, c.name, self.tablename, c.name))
                # cur.execute('ALTER TABLE %s ADD PRIMARY KEY ( "_parent", "%s" )' % (self.tablename, c.name))
    
    
class ModelManager(object):
    modelconfig = gripe.Config.model
    models = modelconfig.get("model", {})
    def_recon_policy = modelconfig.get("reconcile", "none")
    _adapters = { "sqlite3": Sqlite3Adapter, "postgresql": PostgresqlAdapter }

    def __init__(self, name):
        logger.debug("ModelManager.__init__(%s)", name)
        self.my_config = self.models.get(name, {})
        self.name = name
        self._adapter = self._adapters[gripe.db.Tx.database_type](self) 
        self.table = name
        self.tablename = self.tableprefix + '"' + name + '"'
        self.columns = None
        self._prep_columns = []
        self.kind = None
        self.key_col = None
        self.flat = False
        self.audit = True

    def __str__(self):
        return "ModelManager <%s>" % self.name

    def set_tablename(self, tablename):
        self.table = tablename
        self.tablename = self.tableprefix + '"' + tablename + '"'

    def _set_columns(self):
        logger.debug("%s: set_columns(%s)", self, len(self._prep_columns))
        self.key_col = None
        for c in self._prep_columns:
            if c.is_key:
                logger.debug("%s: _set_columns: found key_col: %s", self, c.name)
                self.key_col = c
                c.required = True
        self.columns = []
        if not self.key_col:
            logger.debug("%s: _set_columns: Adding synthetic key_col", self)
            kc = ColumnDefinition("_key_name", "TEXT", True, None, False)
            kc.is_key = True
            kc.scoped = False
            self.key_col = kc
            self.columns.append(kc)
        if not self.flat:
            logger.debug("%s: _set_columns: Adding _ancestors and _parent columns", self)
            self.columns += (ColumnDefinition("_ancestors", "TEXT", True, None, True), \
                ColumnDefinition("_parent", "TEXT", False, None, True))
        self.columns += self._prep_columns
        if self.audit:
            logger.debug("%s: _set_columns: Adding audit columns", self)
            self.columns += (ColumnDefinition("_ownerid", "TEXT", False, None, True), \
                ColumnDefinition("_acl", "TEXT", False, None, False), \
                ColumnDefinition("_createdby", "TEXT", False, None, False), \
                ColumnDefinition("_created", "TIMESTAMP", False, None, False), \
                ColumnDefinition("_updatedby", "TEXT", False, None, False), \
                ColumnDefinition("_updated", "TIMESTAMP", False, None, False))
        self.column_names = [c.name for c in self.columns]

    def add_column(self, column):
        assert self.kind, "ModelManager for %s without kind set??" % self.name
        assert not self.kind._sealed, "Kind %s is sealed" % self.name
        if isinstance(column, (tuple, list)):
            for c in column:
                self.add_column(c)
        else:
            logger.debug("%s: add_column(%s)", self, column.name)
            self._prep_columns.append(column)

    def reconcile(self):
        logger.info("%s: reconcile()", self)
        self._set_columns()
        self._recon = self.my_config.get("reconcile", self.def_recon_policy)
        if self._recon != "none":
            with gripe.db.Tx.begin() as tx:
                cur = tx.get_cursor()
                if self._recon == "drop":
                    logger.info("%s: reconcile() drops table", self)
                    cur.execute('DROP TABLE IF EXISTS ' + self.tablename)
                    self._create_table(cur)
                else:  # _recon is 'all' or 'add'
                    if not self._table_exists(cur):
                        self._create_table(cur)
                    else:
                        self._update_table(cur)

    def _table_exists(self, cur):
        return self._adapter.table_exists(cur)

    def _create_table(self, cur):
        logger.info("%s: reconcile() creates table", self)
        sql = 'CREATE TABLE %s (' % self.tablename
        vars = []
        cols = []
        for c in self.columns:
            csql = '\n"%s" %s' % (c.name, c.data_type)
            if c.required:
                csql += " NOT NULL"
            if c.defval:
                csql += " DEFAULT ( %s )"
                vars.append(c.defval)
            if c.is_key and not c.scoped:
                csql += " PRIMARY KEY"
            cols.append(csql)
        sql += ",".join(cols) + "\n)"
        cur.execute(sql, vars)
        for c in self.columns:
            if c.indexed and not c.is_key:
                cur.execute('CREATE INDEX "%s_%s" ON %s ( "%s" )' % (self.table, c.name, self.tablename, c.name))
            if c.is_key and c.scoped:
                cur.execute('CREATE UNIQUE INDEX "%s_%s" ON %s ( "_parent", "%s" )' % (self.table, c.name, self.tablename, c.name))

    def _update_table(self, cur, table_existed = False):
        self._adapter.update_table(cur, table_existed)

    modelmanagers_byname = {}

    @classmethod
    def for_name(cls, name):
        if name in cls.modelmanagers_byname:
            ret = cls.modelmanagers_byname[name]
        else:
            logger.debug("%s.for_name(%s) *not* found. Creating", cls.__name__, name)
            ret = ModelManager(name)
            cls.modelmanagers_byname[name] = ret
        return ret

