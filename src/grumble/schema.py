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

class ModelManager(object):
    modelconfig = gripe.Config.model
    models = modelconfig.get("model", {})
    def_recon_policy = modelconfig.get("reconcile", "all")

    def __init__(self, name):
        logger.debug("ModelManager.__init__(%s)", name)
        self.my_config = self.models.get(name, {})
        self.name = name
        self.schema = gripe.Config.database.postgresql.schema
        self.tableprefix = '"%s".' % gripe.Config.database.postgresql.schema \
            if gripe.Config.database.postgresql.schema else ""
        self.table = name
        self.tablename = self.tableprefix + '"' + name + '"'
        self.columns = None
        self._prep_columns = []
        self.kind = None
        self.key_col = None
        self.flat = False
        self.audit = True

    def set_tablename(self, tablename):
        self.table = tablename
        self.tablename = self.tableprefix + '"' + tablename + '"'

    def _set_columns(self):
        logger.debug("%s.set_columns(%s)", self.name, len(self._prep_columns))
        self.key_col = None
        for c in self._prep_columns:
            if c.is_key:
                logger.debug("%s._set_columns: found key_col: %s", self.name, c.name)
                self.key_col = c
                c.required = True
        self.columns = []
        if not self.key_col:
            logger.debug("%s.set_columns: Adding synthetic key_col", self.name)
            kc = ColumnDefinition("_key_name", "TEXT", True, None, False)
            kc.is_key = True
            kc.scoped = False
            self.key_col = kc
            self.columns.append(kc)
        if not self.flat:
            self.columns += (ColumnDefinition("_ancestors", "TEXT", True, None, True), \
                ColumnDefinition("_parent", "TEXT", False, None, True))
        self.columns += self._prep_columns
        if self.audit:
            self.columns += (ColumnDefinition("_ownerid", "TEXT", False, None, True), \
                ColumnDefinition("_acl", "TEXT", False, None, False), \
                ColumnDefinition("_createdby", "TEXT", False, None, False), \
                ColumnDefinition("_created", "TIMESTAMP", False, None, False), \
                ColumnDefinition("_updatedby", "TEXT", False, None, False), \
                ColumnDefinition("_updated", "TIMESTAMP", False, None, False))
        self.column_names = [c.name for c in self.columns]
        logger.debug("_set_columns(%s) -> colnames %s", self.name, self.column_names)

    def add_column(self, column):
        assert self.kind, "ModelManager for %s without kind set??" % self.name
        assert not self.kind._sealed, "Kind %s is sealed" % self.name
        if isinstance(column, (tuple, list)):
            for c in column:
                self.add_column(c)
        else:
            logger.debug("add_column: %s", column.name)
            self._prep_columns.append(column)

    def reconcile(self):
        self._set_columns()
        self._recon = self.my_config.get("reconcile", self.def_recon_policy)
        if self._recon != "none":
            with gripe.db.Tx.begin() as tx:
                cur = tx.get_cursor()
                if self._recon == "drop":
                    cur.execute('DROP TABLE IF EXISTS ' + self.tablename)
                    self._create_table(cur)
                else:  # _recon is 'all' or 'add'
                    if not self._table_exists(cur):
                        self._create_table(cur)
                    else:
                        self._update_table(cur)

    def _table_exists(self, cur):
        sql = "SELECT table_name FROM information_schema.tables WHERE table_name = %s"
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        return cur.fetchone() is not None

    def _create_table(self, cur):
        cur.execute('CREATE TABLE %s ( )' % (self.tablename,))
        self._update_table(cur)

    def _update_table(self, cur):
        sql = "SELECT column_name, column_default, is_nullable, data_type FROM information_schema.columns WHERE table_name = %s"
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        coldescs = []
        for coldesc in cur:
            coldescs.append(coldesc)
        for (colname, defval, is_nullable, data_type) in coldescs:
            column = None
            for c in self.columns:
                if c.name == colname:
                    column = c
                    break
            if column:
                if data_type.lower() != column.data_type.lower():
                    logger.info("Data type change: %s.%s %s -> %s", \
                                    self.tablename, colname, data_type.lower(), \
                                    column.data_type.lower())
                    cur.execute('ALTER TABLE ' + self.tablename + ' DROP COLUMN "' + colname + '"')
                    # We're not removing the column from the dict -
                    # we'll re-add the column when we add 'new' columns
                else:
                    if self._recon == "all":
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
                    self.columns.remove(column)
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
                # cur.execute('ALTER TABLE %s ADD PRIMARY KEY ( "_parent", "%s" )' % (self.tablename, c.name))

    modelmanagers_byname = {}
    @classmethod
    def for_name(cls, name):
        logger.debug("%s.for_name(%s)", cls.__name__, name)
        logger.debug("Current registry: %s", cls.modelmanagers_byname)
        if name in cls.modelmanagers_byname:
            logger.debug("%s.for_name(%s) found", cls.__name__, name)
            ret = cls.modelmanagers_byname[name]
        else:
            logger.debug("%s.for_name(%s) *not* found. Creating", cls.__name__, name)
            ret = ModelManager(name)
            cls.modelmanagers_byname[name] = ret
        return ret

