# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$19-Jan-2013 11:19:59 AM$"

import base64
import datetime
import json
import logging
import os
import os.path
import sha
import sys
import threading
import traceback
import uuid

import gripe
from gripe import json_util
from gripe import pgsql

logger = gripe.get_logger(__name__)

class PropertyRequired(gripe.Error):
    """Raised when no value is specified for a required property"""
    def __init__(self, propname):
        self.propname = propname

    def __str__(self):
        return "Property %s requires a value" % (self.propname,)

class InvalidChoice(gripe.Error):
    """Raised when a value is specified for a property that is not in the
    property's <tt>choices</tt> list"""
    def __init__(self, propname, value):
        self.propname = propname
        self.value = value

    def __str__(self):
        return "Value %s is invalid for property %s" % (self.value, self.propname)

class ObjectDoesNotExist(gripe.Error):
    """Raised when an object is requested that does not exist"""
    def __init__(self, cls, id):
        self.cls = cls
        self.id = id

    def __str__(self):
        return "Model %s:%s does not exist" % (self.cls.__name__, self.id)

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
        assert config.postgresql, "Config: conf/database.json is missing postgresql section"
        pgsql_conf = config.postgresql
        assert pgsql_conf.user, "Config: No user role in postgresql section of conf/database.json"
        pgsql_user = pgsql_conf.user
        assert pgsql_conf.admin, "Config: No admin role in postgresql section of conf/database.json"
        pgsql_admin = pgsql_conf.admin
        assert pgsql_user.user_id and pgsql_user.password, \
            "Config: user role is missing user_id or password in postgresql section of conf/database.json"
        assert pgsql_admin.user_id and pgsql_admin.password, \
            "Config: admin role is missing user_id or password in postgresql section of conf/database.json"

        if pgsql_conf.database:
            database = pgsql_conf.database
            if database != 'postgres':
                # We're assuming the postgres database exists and should never be wiped:
                with Tx.begin("admin", "postgres", True) as tx:
                    cur = tx.get_cursor()
                    create_db = False
                    if isinstance(pgsql_conf.wipe_database, bool) and pgsql_conf.wipe_database:
                        cur.execute('DROP DATABASE IF EXISTS "%s"' % (database,))
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
                if isinstance(pgsql_conf.wipe_schema, bool) and pgsql_conf.wipe_schema:
                    cur.execute('DROP SCHEMA IF EXISTS "%s" CASCADE' % (schema,))
                    create_schema = True
                else:
                    cur.execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s", (schema,))
                    create_schema = (cur.fetchone()[0] == 0)
                if create_schema:
                    cur.execute('CREATE SCHEMA "%s" AUTHORIZATION %s' % (schema, pgsql_conf["user"]["user_id"]))

    def _connect(self):
        config = gripe.Config.database
        pgsql_conf = config.postgresql
        dsn = "user=%s password=%s" % (getattr(pgsql_conf, self.role).user_id, getattr(pgsql_conf, self.role).password)
        if not self.database:
            self.database = pgsql_conf.database
        if not self.database:
            self.database = "postgres" if self.role == "admin" else getattr(pgsql_conf, self.role).user_id
        dsn += " dbname=%s" % self.database
        if pgsql_conf.host:
            dsn += " host=%s" % pgsql_conf.host
        logger.debug("Connecting with role '%s' autocommit = %s", self.role, self.autocommit)
        self.conn = pgsql.Connection.get(dsn)
        self.conn.autocommit = self.autocommit

    @classmethod
    def begin(cls, role = "user", database = None, autocommit = False):
        return cls._tl.tx if hasattr(cls._tl, "tx") else Tx(role, database, autocommit)

    @classmethod
    def get(cls):
        return cls._tl.tx if hasattr(cls._tl, "tx") else None

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, exception_type, exception_value, trace):
        self.count -= 1
        if exception_type:
            logger.error("Exception in Tx block, Exception: %s %s %s", exception_type, exception_value, trace)
        if not self.count:
            try:
                self._end_tx()
            except Exception, exc:
                logger.error("Exception committing Tx, Exception: %s %s", exc.__class__.__name__, exc)
        return False

    def get_cursor(self):
        ret = self.conn.cursor()
        self.cursors.append(ret)
        return ret

    def close_cursor(self, cur):
        self.cursors.remove(cur)
        cur.close()

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

    @classmethod
    def get_from_cache(cls, key):
        tx = cls.get()
        return (tx.cache[key] if key in tx.cache else None) if tx else None

    @classmethod
    def put_in_cache(cls, model):
        tx = cls.get()
        if tx:
            tx.cache[model.key()] = model

    @classmethod
    def flush_cache(cls):
        tx = cls.get()
        if tx:
            del tx.cache
            tx.cache = {}

_sessionbridge = None
def set_sessionbridge(bridge):
    global _sessionbridge
    _sessionbridge = bridge

def get_sessionbridge():
    global _sessionbridge
    if not _sessionbridge:
        from gripe import sessionbridge
        _sessionbridge = sessionbridge.sessionbridge
    return _sessionbridge

class ColumnDefinition(object):
    def __init__(self, name, data_type, required, defval, indexed):
        self.name = name
        self.data_type = data_type
        self.required = required
        self.defval = defval
        self.indexed = indexed
        self.is_key = False

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

    def set_columns(self):
        logger.debug("%s.set_columns(%s)", self.name, len(self._prep_columns))
        self.key_col = None
        for c in self._prep_columns:
            if c.is_key and not c.scoped:
                logger.debug("%s.set_columns: found key_col: %s", self.name, c.name)
                self.key_col = c
                c.required = True
        self.columns = []
        if not self.key_col:
            logger.debug("%s.set_columns: Adding synthetic key_col", self.name)
            kc = ColumnDefinition("_key_name", "TEXT", True, None, False)
            kc.is_key = True
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

    def add_column(self, column):
        if isinstance(column, (tuple, list)):
            for c in column:
                self.add_column(c)
        else:
            if self.columns:
                self.columns.append(column)
                self.column_names.append(column.name)
            else:
                logger.debug("add_column: %s", column.name)
                self._prep_columns.append(column)

    def get_properties(self, key):
        ret = None
        with Tx.begin() as tx:
            cur = tx.get_cursor()
            sql = 'SELECT "%s" FROM %s WHERE "%s" = %%s' % \
                ('", "'.join(self.column_names), self.tablename, self.key_col.name)
            cur.execute(sql, (key.name,))
            values = cur.fetchone()
            if values:
                ret = zip(self.column_names, values)
        return ret

    def set_properties(self, insert, key, values):
        logger.debug("ModelManager.set_properties(%s)", values)
        if self.audit:
            values["_updated"] = datetime.datetime.now()
            values["_updatedby"] = get_sessionbridge().userid()
            if insert:
                values["_created"] = values["_updated"]
                values["_createdby"] = values["_updatedby"]
                if not values.get("_ownerid"):
                    values["_ownerid"] = values["_createdby"]
            else:
                if "_created" in values:
                    values.pop("_created")
                if "_createdby" in values:
                    values.pop("_createdby")
        ret = key.id
        with Tx.begin() as tx:
            assert key.name
            cur = tx.get_cursor()
            cols = set(self.column_names) & set(values.keys())
            v = [values[c] for c in cols]
            if insert:
                sql = 'INSERT INTO %s ( "%s" ) VALUES ( %s )' % \
                    (self.tablename, '", "'.join(cols), ', '.join(['%s'] * len(cols)))
            else:
                sql = 'UPDATE %s SET %s WHERE "%s" = %%s' % \
                    (self.tablename, ", ".join(['"%s" = %%s' % c for c in cols]), self.key_col.name)
                v.append(key.name)
            cur.execute(sql, v)
        return ret

    def delete_one(self, key):
        with Tx.begin() as tx:
            cur = tx.get_cursor()
            sql = 'DELETE FROM %s WHERE "%s" = %%s' % (self.tablename, self.key_col.name)
            cur.execute(sql, (key.name,))

    def query(self, ancestor, filters, what = "key_name"):
        key_ix = 0
        if what == "delete":
            sql = "DELETE FROM %s" % self.tablename
            cols = ()
            key_ix = -1
        else:
            if what == "columns":
                cols = [c.name for c in self.columns]
                collist = '"' + '", "'.join(cols) + '"'
                key_ix = cols.index(self.key_col.name)
            elif what == "key_name":
                cols = (self.key_col.name,)
                collist = '"%s"' % cols[0]
            else:
                collist = what
                cols = (what,)
            sql = 'SELECT %s FROM %s' % (collist, self.tablename)
        vals = []
        glue = ' WHERE '
        if ancestor:
            assert not self.flat, "Cannot perform ancestor queries on flat tables"
            glue = ' AND '
            if ancestor != "/":
                sql += ' WHERE "_ancestors" LIKE %s'
                vals.append(ancestor + "%")
            else:
                sql += ' WHERE "_ancestors" = %s' % "'/'"
        if filters:
            filtersql = " AND ".join(['%s %%s' % e for (e, v) in filters])
            sql += glue + filtersql
            vals += [v for (e, v) in filters]
        tx = Tx.get()
        assert tx, "ModelManager.query: no transaction active"
        cur = tx.get_cursor()
        cur.execute(sql, vals)
        return (cur, cols, key_ix)

    def _next_batch(self, cur):
        if not cur.closed:
            ret = cur.fetchmany()
            if len(ret) < cur.arraysize:
                logger.debug("ModelManager.query: no more results, closing cursor")
                tx = Tx.get()
                assert tx, "ModelManager.query: no transaction active"
                tx.close_cursor(cur)
        else:
            ret = None
        return ret

    def count(self, ancestor, filters):
        (cur, ignored1, ignored2) = self.query(ancestor, filters, 'COUNT(*)')
        ret = cur.fetchone()[0]
        tx = Tx.get()
        tx.close_cursor(cur)
        return ret

    def delete_query(self, ancestor, filters):
        (cur, ignored1, ignored2) = self.query(ancestor, filters, 'delete')
        ret = cur.rowcount
        tx = Tx.get()
        tx.close_cursor(cur)
        return ret

    def reconcile(self):
        self._recon = self.my_config.get("reconcile", self.def_recon_policy)
        if self._recon != "none":
            with Tx.begin() as tx:
                cur = tx.get_cursor()
                if self._recon == "drop":
                    cur.execute('DROP TABLE IF EXISTS ' + self.tablename)
                    self.create_table(cur)
                else:  # _recon is 'all' or 'add'
                    if not self.table_exists(cur):
                        self.create_table(cur)
                    else:
                        self.update_table(cur)

    def table_exists(self, cur):
        sql = "SELECT table_name FROM information_schema.tables WHERE table_name = %s"
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        return cur.fetchone() is not None

    def create_table(self, cur):
        cur.execute('CREATE TABLE %s ( )' % (self.tablename,))
        self.update_table(cur)

    def update_table(self, cur):
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
                    logger.info("Data type change: %s.%s %s -> %s", self.tablename, colname, data_type.lower(), column.data_type.lower())
                    cur.execute('ALTER TABLE ' + self.tablename + ' DROP COLUMN "' + colname + '"')
                    # We're not removing the column from the dict -
                    # we'll re-add the column when we add 'new' columns
                else:
                    if self._recon == "all":
                        alter = ""
                        vars = []
                        if column.required != (is_nullable == 'NO'):
                            logger.info("NULL change: %s.%s required %s -> is_nullable %s", self.tablename, colname, column.required, is_nullable)
                            alter = " SET NOT NULL" if column.required else " DROP NOT NULL"
                        if column.defval != defval:
                            alter += " DEFAULT %s"
                            vars.append(column.defval)
                        if alter != "":
                            cur.execute('ALTER TABLE %s ALTER COLUMN "%s" %s' % (self.tablename, colname, alter), vars)
                    self.columns.remove(column)
        for c in self.columns:
            vars = []
            sql = 'ALTER TABLE ' + self.tablename + ' ADD COLUMN "' + c.name + '" ' + c.data_type
            if c.required:
                sql += " NOT NULL"
            if c.defval:
                sql += " DEFAULT %s"
                vars.append(c.defval)
            if c.is_key:
                sql += " PRIMARY KEY"
            cur.execute(sql, vars)
            if c.indexed and not c.is_key:
                cur.execute('CREATE INDEX "%s_%s" ON %s ( "%s" )' % (self.table, c.name, self.tablename, c.name))

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

class PropertyConverter(object):
    def __init__(self, datatype):
        self.datatype = datatype

    def convert(self, value):
        try:
            return self.datatype(value) if not isinstance(value, self.datatype) else value
        except:
            logger.debug("converter: %s - value %s - datatype %s", self.__class__.__name__, value, self.datatype)
            raise

    def to_sqlvalue(self, value):
        return value

    def from_sqlvalue(self, value):
        return value

    def to_jsonvalue(self, value):
        return value

    def from_jsonvalue(self, value):
        return value

class DictConverter(PropertyConverter):
    def convert(self, value):
        if isinstance(value, dict):
            return dict(value)
        elif value is None:
            return {}
        else:
            return json.loads(str(value))

    def to_sqlvalue(self, value):
        assert (value is None) or isinstance(value, dict), "DictConverter.to_sqlvalue(): value must be a dict"
        return json.dumps(value if value else {})

    def from_sqlvalue(self, sqlvalue):
        return json.loads(sqlvalue) if sqlvalue else {}

    def to_jsonvalue(self, value):
        assert value is not None, "DictConverter.to_jsonvalue(): value should not be None"
        assert isinstance(value, dict), "DictConverter.to_jsonvalue(): value must be a dict"
        return dict(value)

    def from_jsonvalue(self, value):
        assert (value is None) or isinstance(value, dict), "DictConverter.to_sqlvalue(): value must be a dict"
        return value or {}

class ListConverter(PropertyConverter):
    def convert(self, value):
        try:
            return list(value)
        except:
            return json.loads(str(value)) if value is not None else {}

    def to_sqlvalue(self, value):
        assert (value is None) or isinstance(value, list), "ListConverter.to_sqlvalue(): value must be a list"
        return json.dumps(value if value else [])

    def from_sqlvalue(self, sqlvalue):
        return json.loads(sqlvalue) if sqlvalue else {}

    def to_jsonvalue(self, value):
        assert value is not None, "ListConverter.to_jsonvalue(): value should not be None"
        assert isinstance(value, list), "ListConverter.to_jsonvalue(): value must be a list"
        return list(value)

    def from_jsonvalue(self, value):
        assert (value is None) or isinstance(value, list), "ListConverter.to_sqlvalue(): value must be a list"
        return value or []

class DateTimeConverter(PropertyConverter):
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.datetime), "DateTimeConverter.to_jsonvalue: value must be datetime"
        return json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return json_util.dict_to_datetime(value) if isinstance(value, dict) else value

class DateConverter(PropertyConverter):
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.date), "DateConverter.to_jsonvalue: value must be date"
        return json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return json_util.dict_to_datetime(value) if isinstance(value, dict) else value

class TimeConverter(PropertyConverter):
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.datetime), "TimeConverter.to_jsonvalue: value must be time"
        return json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return json_util.dict_to_datetime(value) if isinstance(value, dict) else value

_converters = { \
    dict: DictConverter(dict), \
    list: ListConverter(list), \
    datetime.datetime: DateTimeConverter(datetime.datetime), \
    datetime.date: DateConverter(datetime.date), \
    datetime.time: TimeConverter(datetime.time), \
}

def register_propertyconverter(datatype, converter):
    _converters[datatype] = converter

class ModelProperty(object):
    def __new__(cls, *args, **kwargs):
        ret = super(ModelProperty, cls).__new__(cls)
        ret.name = args[0] if args else None
        ret.column_name = kwargs.get("column_name", None)
        ret.verbose_name = kwargs.get("verbose_name", ret.name)
        ret.required = kwargs.get("required", False)
        ret.default = kwargs.get("default", None)
        ret.private = kwargs.get("private", False)
        ret.transient = kwargs.get("transient", False)
        ret.is_label = kwargs.get("is_label", False)
        ret.is_key = kwargs.get("is_key", False)
        ret.scoped = kwargs.get("scoped", False) if ret.is_key else False
        ret.indexed = kwargs.get("indexed", False)
        ret.validator = kwargs.get("validator", None)
        assert (ret.validator is None) or callable(ret.validator), "Validator %s must be function, not %s" % (str(ret.validator), type(ret.validator))
        ret.converter = kwargs.get("converter", \
            cls.converter \
                if hasattr(cls, "converter") \
                else _converters.get(cls.datatype, PropertyConverter(cls.datatype))
        )
        ret.suffix = kwargs.get("suffix", None)
        ret.choices = kwargs.get("choices", None)
        return ret

    def set_name(self, name):
        self.name = name
        if not self.column_name:
            self.column_name = name
        if not self.verbose_name:
            self.verbose_name = name

    def set_kind(self, kind):
        self.kind = kind

    def get_coldef(self):
        ret = ColumnDefinition(self.column_name, self.sqltype, self.required, self.default, self.indexed)
        ret.is_key = self.is_key
        ret.scoped = self.scoped
        return [ret]

    def _on_insert(self, instance):
        value = self.__get__(instance)
        if not value and self.default:
            return self.__set__(instance, self.default)

    def _initial_value(self):
        return self.default

    def _on_store(self, value):
        pass

    def validate(self, value):
        if (value is None) and self.required:
            raise PropertyRequired(self.name)
        if self.choices and value not in self.choices:
            raise InvalidChoice(self.name, value)
        if self.validator:
            self.validator(value)

    def _update_fromsql(self, instance, values):
        instance._values[self.name] = self._from_sqlvalue(values[self.column_name])

    def _values_tosql(self, instance, values):
        values[self.column_name] = self._to_sqlvalue(self.__get__(instance))

    def __get__(self, instance, owner = None):
        if not instance:
            return self
        instance._load()
        return instance._values[self.name] if self.name in instance._values else None

    def __set__(self, instance, value):
        if self.is_key and not hasattr(instance, "_brandnew"):
            return
        instance._load()
        instance._values[self.name] = self.convert(value) if value is not None else None

    def __delete__(self, instance):
        return NotImplemented

    def convert(self, value):
        return self.converter.convert(value)

    def _to_sqlvalue(self, value):
        return self.converter.to_sqlvalue(value)

    def _from_sqlvalue(self, sqlvalue):
        return self.converter.from_sqlvalue(sqlvalue)

    def from_json_value(self, instance, values):
        v = values.get(self.name, None)
        try:
            v = self.datatype.from_dict(v)
        except:
            try:
                v = self.converter.from_jsonvalue(v)
            except:
                pass
        setattr(instance, self.name, v)

    def to_json_value(self, instance, values):
        v = getattr(instance, self.name)
        try:
            v = v.to_dict()
        except:
            try:
                v = self.converter.to_jsonvalue(v)
            except:
                pass
        values[self.name] = v
        return values


class CompoundProperty(object):
    def __init__(self, *args, **kwargs):
        self.compound = []
        for p in args:
            self.compound.append(p)
        self.verbose_name = kwargs.get("verbose_name", None)
        if "name" in kwargs:
            self.set_name(kwargs["name"])
        self.private = kwargs.get("private", False)
        self.transient = kwargs.get("transient", False)
        self.validator = kwargs.get("validator", None)
        self.is_key = False
        self.is_label = False

    def set_name(self, name):
        self.name = name
        if not self.verbose_name:
            self.verbose_name = name
        for p in self.compound:
            if p.suffix:
                p.set_name(name + p.suffix)

    def set_kind(self, kind):
        self.kind = kind
        for prop in self.compound:
            prop.set_kind(kind)

    def get_coldef(self):
        ret = []
        for prop in self.compound:
            ret += prop.get_coldef()
        return ret

    def _on_insert(self, instance):
        for p in self.compound:
            p._on_insert(instance)

    def _on_store(self, instance):
        for p in self.compound:
            p._on_store(instance)

    def validate(self, value):
        for (p, v) in zip(self.compound, value):
            p.validate(v)
        if self.validator:
            self.validator(value)

    def _initial_value(self):
        return tuple(p._initial_value() for p in self.compound)

    def _update_fromsql(self, instance, values):
        for p in self.compound:
            p._update_fromsql(instance, values)

    def _values_tosql(self, instance, values):
        for p in self.compound:
            p._values_tosql(instance, values)

    def __get__(self, instance, owner):
        if not instance:
            return self
        instance._load()
        return tuple(p.__get__(instance, owner) for p in self.compound)

    def __set__(self, instance, value):
        instance._load()
        for (p, v) in zip(self.compound, value):
            p.__set__(instance, v)

    def __delete__(self, instance):
        return NotImplemented

    def convert(self, value):
        return tuple(p.convert(v) for (p, v) in zip(self.compound, value))

    def from_json_value(self, instance, values):
        for p in filter(lambda p: not p.private, self.compound):
            p.from_json_value(instance, values)

    def to_json_value(self, instance, values):
        for p in filter(lambda p: not p.private, self.compound):
            values = p.to_json_value(instance, values)
        return values


class LoopDetector(set):
    _tl = threading.local()

    def __init__(self):
        self.count = 0
        LoopDetector._tl.detector = self

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, *args):
        self.count -= 1
        if not self.count:
            del LoopDetector._tl.detector

    @classmethod
    def begin(cls):
        return LoopDetector._tl.detector if hasattr(LoopDetector._tl, "detector") else LoopDetector()


def _set_acl(obj, acl):
    if isinstance(acl, dict):
        obj._acl = dict(acl)
    elif isinstance(acl, basestring):
        obj._acl = json.loads(acl)
    else:
        obj._acl = {}
    for (role, perms) in obj._acl.items():
        assert role and role.lower() == role, "Model._set_acl: Role may not be None and and must belower case"
        assert perms and perms.upper() == perms, "Model._set_acl: Permissions may not be None and must be upper case"

class ModelMetaClass(type):
    def __new__(cls, name, bases, dct):
        kind = type.__new__(cls, name, bases, dct)
        if name != 'Model':
            kind._sealed = False
            Model._register_class(cls.__module__, name, kind)
            if hasattr(kind, "table_name"):
                tablename = kind.table_name
            else:
                tablename = name
                kind.table_name = name
            kind._flat = kind._flat if hasattr(kind, "_flat") else False
            kind._audit = kind._audit if hasattr(kind, "_audit") else True
            kind._parentclass = (Model.for_name(kind._parentclass) if isinstance(kind._parentclass, basestring) else kind._parentclass) \
                if hasattr(kind, "_parentclass") else None
            acl = Config.model["model"][name]["acl"] \
                if "model" in gripe.Config.model and \
                    name in gripe.Config.model["model"] and \
                    "acl" in gripe.Config.model["model"][name] \
                else kind.acl if hasattr(kind, "acl") else None
            _set_acl(kind, acl)
            kind._properties = {}
            kind._allproperties = {}
            kind._query_properties = {}
            mm = ModelManager.for_name(kind._kind)
            for (propname, value) in dct.items():
                ModelMetaClass.add_property(kind, propname, value)
            mm.flat = kind._flat
            mm.audit = kind._audit
            mm.set_tablename(tablename)
            mm.set_columns()
            mm.kind = kind
            mm.reconcile()
            kind.modelmanager = mm
            kind.load_template_data()
        else:
            _set_acl(kind, gripe.Config.model.get("global_acl", kind.acl))
        return kind

    @staticmethod
    def add_property(model, propname, propdef):
        if not isinstance(propdef, (ModelProperty, CompoundProperty)):
            return
        assert not model._sealed, "Model %s is sealed. No more properties can be added" % model.__name__
        propdef.set_name(propname)
        propdef.set_kind(model.__name__)
        mm = ModelManager.for_name(model._kind)
        if not propdef.transient:
            mm.add_column(propdef.get_coldef())
        if hasattr(propdef, "is_label") and propdef.is_label:
            assert not hasattr(model, "label_prop"), "Can only assign one label property"
            model.label_prop = propdef
        if hasattr(propdef, "is_key") and propdef.is_key:
            assert not hasattr(model, "key_prop"), "Can only assign one key property"
            assert not propdef.transient, "Key property cannot be transient"
            model.key_prop = propdef
        model._properties[propname] = propdef
        model._allproperties[propname] = propdef
        if isinstance(propdef, CompoundProperty):
            for p in propdef.compound:
                setattr(model, p.name, p)
                model._allproperties[p.name] = propdef


class Model(object):
    __metaclass__ = ModelMetaClass
    classes = {}
    acl = { "admin": "RUDQC", "owner": "R" }

    def __new__(cls, *args, **kwargs):
        cls._sealed = True
        ret = super(Model, cls).__new__(cls)
        ret._brandnew = True
        ret._set_ancestors_from_parent(kwargs["parent"] if "parent" in kwargs else None)
        ret._key_name = kwargs["key_name"] if "key_name" in kwargs else None
        ret._acl = kwargs["acl"] if "acl" in kwargs else {}
        ret._id = None
        ret._values = {}
        for (propname, prop) in ret._allproperties.items():
            setattr(ret, propname, prop._initial_value())
        for (propname, propvalue) in kwargs.items():
            if propname in ret._allproperties:
                setattr(ret, propname, propvalue)
        logger.debug("%s.__new__: %s", ret.kind(), ret._values)
        return ret

    def __repr__(self):
        return str(self.key())

    def __str__(self):
        self._load()
        label = self.label_prop if hasattr(self.__class__, "label_prop") else None
        if self.name():
            s = self.name()
            if label:
                s += " (%s)" % label
            return "<%s: %s>" % (self.kind(), s)
        else:
            super(self.__class__, self).__repr__()

    def __hash__(self):
        return hash(self.id())

    def __eq__(self, other):
        assert isinstance(other, Model)
        return (self.kind() == other.kind()) and (self.name() == other.name())

    def _set_ancestors_from_parent(self, parent):
        if not self._flat:
            if parent:
                parent = Key(parent)
            assert parent is None or isinstance(parent, Key)
            self._parent = parent
            if parent:
                p = parent.get()
                self._ancestors = p.path()
            else:
                self._ancestors = "/"
        else:
            self._parent = None
            self._ancestors = "/"

    def _set_ancestors(self, ancestors, parent):
        if not self._flat:
            if ancestors == "/":
                self._parent = None
                self._ancestors = "/"
            elif isinstance(ancestors, basestring):
                self._ancestors = ancestors
                (a, sep, p) = ancestors.rpartition("/")
                assert p == str(parent)
                self._parent = Key(p)
        else:
            self._parent = None
            self._ancestors = "/"

    def _populate(self, values):
        logger.debug("%s._populate(%s)", self.kind(), values)
        if values is not None:
            self._values = {}
            v = {}
            for (name, value) in values:
                v[name] = value
            parent = v["_parent"] if "_parent" in v else None
            ancestors = v["_ancestors"] if "_ancestors" in v else None
            self._key_name = v["_key_name"] if "_key_name" in v else None
            self._ownerid = v["_ownerid"] if "_ownerid" in v else None
            _set_acl(self, v["_acl"] if "_acl" in v else None)
            for prop in self._properties.values():
                prop._update_fromsql(self, v)
            if (self._key_name is None) and hasattr(self, "key_prop"):
                self._key_name = self.key_prop
            self._set_ancestors(ancestors, parent)
            self._exists = True
            self._id = self.key().id
        else:
            self._exists = False

    def _load(self):
        if (not hasattr(self, "_values") or (self._values is None)) and (self._id or self._key_name):
            self._populate(self.modelmanager.get_properties(self.key()))

    def _store(self):
        self._load()
        logger.info("Storing model %s.%s", self.kind(), self.key())
        include_key_name = True
        if hasattr(self, "key_prop"):
            scoped = getattr(self.__class__, "key_prop").scoped
            key = self.key_prop
            self._key_name = "%s/%s" % (self.parent(), key) if scoped else key
            include_key_name = scoped
        elif not self._key_name:
            self._key_name = uuid.uuid1().hex
        self._id = None
        if hasattr(self, "_brandnew"):
            for prop in self._properties.values():
                prop._on_insert(self)
            self.initialize()
        for prop in self._properties.values():
            prop._on_store(self)
        self.on_store()
        self.validate()

        values = {}
        for prop in self._properties.values():
            prop._values_tosql(self, values)
        if include_key_name:
            values['_key_name'] = self._key_name
        if not self._flat:
            p = self.parent()
            values['_parent'] = str(p) if p else None
            values['_ancestors'] = self._ancestors
        values["_acl"] = json.dumps(self._acl)
        values["_ownerid"] = self._ownerid if hasattr(self, "_ownerid") else None
        self._id = self.modelmanager.set_properties(hasattr(self, "_brandnew"), self.key(), values)
        if hasattr(self, "_brandnew"):
            del self._brandnew
        Tx.put_in_cache(self)

    def initialize(self):
        pass

    def on_store(self):
        pass

    def on_delete(self):
        pass

    def validate(self):
        for (name, prop) in self._properties.items():
            prop.validate(prop.__get__(self, None))

    def id(self):
        print "id(): _id %s _key_name %s" % (self._id, self._key_name)
        if not self._id and self._key_name:
            self._id = self.key().id
        return self._id

    def name(self):
        return self._key_name

    def label(self):
        return self.label_prop if hasattr(self, "label_prop") else str(self)

    def parent(self):
        self._load()
        return self._parent

    def key(self):
        return Key(self) if self._key_name else None

    def path(self):
        self._load()
        return (self._ancestors if self._ancestors != "/" else "") + "/" + str(self.key())

    def pathlist(self):
        pl = self.path().split("/")
        del pl[0]  # First element is "/" because the path starts with a "/"
        return [Model.get(k) for k in pl]

    def root(self):
        pl = self.pathlist()
        return pl[0] if pl else self

    def ownerid(self):
        self._load()
        return self._ownerid

    def set_ownerid(self, ownerid):
        self._load()
        self._ownerid = ownerid

    def put(self):
        self._store()

    def exists(self):
        if hasattr(self, "_brandnew"):
            return True
        else:
            self._load()
            return self._exists

    def _to_dict(self, d):
        pass

    def to_dict(self):
        with LoopDetector.begin() as detector:
            p = self.parent()
            ret = { "key": self.id(), 'parent': p.id if p else None }
            if self.id() in detector:
                logger.info("to_dict: Loop detected. %s is already serialized", self)
                return ret
            detector.add(self.id())
            logger.debug("to_dict: Added %s to loop detector", self)
            for b in self.__class__.__bases__:
                if hasattr(b, "_to_dict") and callable(b._to_dict):
                    b._to_dict(self, ret)

            def serialize(ret, (name, prop)):
                if prop.private:
                    return ret
                if hasattr(self, "to_dict_" + name) and callable(getattr(self, "to_dict_" + name)):
                    return getattr(self, "to_dict_" + name)(ret)
                else:
                    try:
                        return prop.to_json_value(self, ret)
                    except gripe.NotSerializableError:
                        pass

            ret = reduce(serialize, self.properties().items(), ret)
            ret = reduce(serialize, self._query_properties.items(), ret)
            hasattr(self, "sub_to_dict") and callable(self.sub_to_dict) and self.sub_to_dict(ret)
            return ret

    def _update(self, d):
        pass

    def update(self, descriptor):
        self._load()
        logger.info("Updating model %s.%s using descriptor %s", self.kind(), self.key(), descriptor)
        for b in self.__class__.__bases__:
            if hasattr(b, "_update") and callable(b._update):
                b._update(self, descriptor)
        for name, prop in filter(lambda (name, prop): (not prop.private) and (name in descriptor), self.properties().items()):
            newval = descriptor[name]
            logger.debug("Updating %s.%s to %s", self.kind(), name, newval)
            if hasattr(self, "update_" + name) and callable(getattr(self, "update_" + name)):
                getattr(self, "update_" + name)(descriptor)
            else:
                try:
                    prop.from_json_value(self, descriptor)
                except gripe.NotSerializableError:
                    pass
        self.put()
        if hasattr(self, "on_update") and callable(self.on_update):
            self.on_update(descriptor) and self.put()
        return self.to_dict()

    def invoke(self, method, args, kwargs):
        self._load()
        args = args or []
        kwargs = kwargs or {}
        assert hasattr(self, method) and callable(getattr(self, method)), "%s.%s has not method %s. Can't invoke" % (self.kind(), self.key(), method)
        logger.info("Invoking %s on %s.%s using arguments *%s, **%s", method, self.kind(), self.key(), args, kwargs)
        return getattr(self, method)(*args, **kwargs)

    def get_user_permissions(self):
        roles = set(get_sessionbridge().roles())
        if get_sessionbridge().userid() == self.ownerid():
            roles.add("owner")
        roles.add("world")
        perms = set()
        for role in roles:
            perms |= self.get_all_permissions(role)
        return perms

    @classmethod
    def get_user_classpermissions(cls):
        roles = set(get_sessionbridge().roles())
        roles.add("world")
        perms = set()
        for role in roles:
            perms |= cls.get_class_permissions(role) | Model.get_global_permissions(role)
        return perms

    def get_object_permissions(self, role):
        return set(self._acl.get(role, ""))

    @classmethod
    def get_class_permissions(cls, role):
        return set(cls.acl.get(role, ""))

    @staticmethod
    def get_global_permissions(role):
        return set(Model.acl.get(role, ""))

    def get_all_permissions(self, role):
        return self.get_object_permissions(role) | self.get_class_permissions(role) | self.get_global_permissions(role)

    def set_permissions(self, role, perms):
        assert role, "Model.set_permissions: Role must not be None"
        self._acl[role.lower()] = perms.upper() if perms else ""

    def can_read(self):
        return "R" in self.get_user_permissions()

    def can_update(self):
        return "U" in self.get_user_permissions()

    def can_delete(self):
        return "D" in self.get_user_permissions()

    @classmethod
    def can_query(cls):
        return "Q" in cls.get_user_classpermissions()

    @classmethod
    def can_create(cls):
        return "C" in cls.get_user_classpermissions()

    @classmethod
    def kind(cls):
        return cls._kind

    @classmethod
    def properties(cls):
        return cls._properties

    @classmethod
    def for_name(cls, name):
        name = name.replace('/', '.').lower()
        if name.startswith("."):
            (empty, dot, name) = name.partition(".")
        if name.startswith("__main__."):
            (main, dot, name) = name.partition(".")
        ret = Model.classes[name] if name in Model.classes else None
        if not ret and "." not in name:
            for n in Model.classes:
                e = ".%s" % name
                if n.endswith(e):
                    c = Model.classes[n]
                    assert not ret, "for_name(%s): Already found match %s but there's a second one %s" % \
                        (name, ret.kind(), c.kind())
                    ret = c
        return ret

    @classmethod
    def _register_class(cls, module, name, modelclass):
        assert modelclass, "Model._register_class: empty class name"
        if not module:
            fullname = name
        else:
            module = module.lower()
            hierarchy = module.split(".")
            while hierarchy and hierarchy[0] in [ 'model', '__main__' ]:
                hierarchy.pop(0)
            hierarchy.append(name)
            fullname = ".".join(hierarchy)
        fullname = fullname.lower()
        assert fullname not in cls.classes, "Model._register_class: Class '%s' is already registered" % fullname
        logger.debug("Model._register_class %s => %s", fullname, modelclass)
        Model.classes[fullname] = modelclass
        modelclass._kind = fullname

    @classmethod
    def get(cls, id, values = None):
        cls._sealed = True
        k = Key(id)
        if cls != Model:
            ret = Tx.get_from_cache(k)
            if not ret:
                ret = super(Model, cls).__new__(cls)
                assert (cls.kind().endswith(k.kind)) or not k.kind, "%s.get(%s.%s) -> wrong key kind" % (cls.kind(), k.kind, k.name)
                ret._id = k.id
                ret._key_name = k.name
                if values:
                    ret._populate(values)
            else:
                # print "%s.get - Cache hit" % cls.__name__
                pass
        else:
            assert k.kind
            return Model.for_name(k.kind).get(k, values)
        return ret

    @classmethod
    def get_by_key(cls, key, values = None):
        cls._sealed = True
        assert cls != Model, "Cannot use get_by_key on unconstrained Models"
        k = Key(cls, key)
        ret = Tx.get_from_cache(k)
        if not ret:
            ret = super(Model, cls).__new__(cls)
            assert (cls.kind().endswith(k.kind)) or not k.kind, "%s.get(%s.%s) -> wrong key kind" % (cls.kind(), k.kind, k.name)
            ret._id = k.id
            ret._key_name = k.name
        return ret

    @classmethod
    def query(cls, *args, **kwargs):
        logger.debug("%s.query: args %s kwargs %s", cls.__name__, args, kwargs)
        assert (args is None) or (len(args) % 2 == 0), "Must specify a value for every filter"
        assert cls != Model, "Cannot query on unconstrained Model class"
        q = Query(cls, kwargs.get("keys_only", True))
        if "ancestor" in kwargs and not cls._flat:
            q.ancestor(kwargs["ancestor"])
        ix = 0
        while ix < len(args):
            q.filter(args[ix], args[ix + 1])
            ix += 2
        return q

    @classmethod
    def create(cls, descriptor = None, parent = None):
        if descriptor is None:
            descriptor = {}
        logger.info("Creating new %s model from descriptor %s", cls.__name__, descriptor)
        kwargs = { "parent": parent }
        kwargs.update(descriptor)
        k = cls.get_new_key(descriptor, parent)
        if k:
            kwargs["key_name"] = k
        obj = cls(**kwargs)
        obj.update(descriptor)
        if hasattr(obj, "on_create") and callable(obj.on_update):
            obj.on_create(descriptor) and obj.put()
        return obj

    @classmethod
    def all(cls, **kwargs):
        return Query(cls, **kwargs)

    @classmethod
    def count(cls, **kwargs):
        return Query(cls).count()

    @classmethod
    def get_new_key(cls, descriptor, parent):
        return None

    @classmethod
    def load_template_data(cls):
        cname = cls.__name__.lower()
        fname = "data/template/" + cname + ".json"
        datastr = gripe.read_file(fname)
        if datastr:
            logger.info("Importing data file %s", fname)
            data = json.loads(datastr)
            if "data" in data:
                for cdata in data["data"]:
                    model = cdata["model"]
                    clazz = Model.for_name(model)
                    if clazz:
                        with Tx.begin():
                            if clazz.all(keys_only = True).count() == 0:
                                logger.info("load_template_data(%s): Loading template model data for model %s", cname, model)
                                for d in cdata["data"]:
                                    logger.debug("load_template_data(%s): model %s object %s", cname, model, d)
                                    clazz.create(d)

def delete(model):
    if not hasattr(model, "_brandnew") and model.exists():
        if model.on_delete():
            mm = model.modelmanager
            logger.info("Deleting model %s.%s", model.kind(), model.key())
            mm.delete_one(model.key())
        else:
            logger.info("on_delete trigger prevented deletion of model %s.%s", model.kind(), model.key())
    return None

class Key(object):
    def __new__(cls, *args):
        if (len(args) == 1) and isinstance(args[0], Key):
            return args[0]
        else:
            return super(Key, cls).__new__(cls)

    def __init__(self, *args):
        if len(args) == 1:
            value = args[0]
            assert value is not None, "Cannot initialize Key from None"
            if isinstance(value, basestring):
                self._assign(value)
            elif isinstance(value, dict):
                if "id" in dict:
                    self.__init__(dict[id])
                else:
                    self.__init__(dict["kind"], dict["name"])
            elif isinstance(value, Model):
                self.kind = value.kind()
                self.id = value._id
                self.name = value.name()
            elif isinstance(value, Key):
                self.kind = value.kind
                self.id = value.id
                self.name = value.name
            else:
                assert 0, "Cannot initialize Key from %s, type %s" % (value, type(value))
            if not (hasattr(self, "id") and self.id) and self.name and self.kind:
                self.id = base64.urlsafe_b64encode("%s:%s" % (self.kind, self.name))
        elif len(args) == 2:
            kind = args[0]
            assert isinstance(kind, basestring) or isinstance(kind, ModelMetaClass), "Second argument of Key(kind, name) must be string or model class, not %s" % type(args[0])
            assert isinstance(args[1], basestring), "Second argument of Key(%s, name) must be string, not %s" % (kind, type(args[1]))
            self._assign("%s:%s" % (kind.kind() if not isinstance(kind, basestring) else kind, args[1]))

    def _assign(self, value):
        value = str(value)
        if value.count(":"):
            s = value
            self.id = base64.urlsafe_b64encode(value)
        else:
            self.id = value
            s = base64.urlsafe_b64decode(value)
        (self.kind, self.name) = s.split(":")

    def __str__(self):
        return self.kind + ":" + self.name

    def __call__(self):
        return self.get()

    def __eq__(self, other):
        assert isinstance(other, Key)
        return (self.kind == other.kind) and (self.name == other.name)

    def __hash__(self):
        return hash(str(self))

    def get(self):
        cls = Model.for_name(self.kind)
        return cls.get(self)

class QueryResults(object):
    def __init__(self, query, kind):
        self.query = query
        self.kind = kind
        self.results = None
        self._mm = None
        self.cur = None
        self.columns = None
        self.iter = None
        self.index_col = None
        self._mm = None
        self._current = None

    def _next_kind(self):
        self.kind = self._q.kind[self._kind_ix] if self._kind_ix < len(self._q.kind) else None
        self._model_ix += 1

    def _next_batch(self):
        self.results = None
        if self._mm is None:
            self._mm = ModelManager.for_name(self.kind)
            (self.cur, self.columns, self.index_col) = \
                self._mm.query(self.query._get_ancestor(), self.query.filters, "key_name" if self.query.keys_only else "columns")
        self.results = self._mm._next_batch(self.cur)

    def __iter__(self):
        return self

    def next(self):
        if not self.results:
            self._next_batch()
            self.iter = iter(self.results)
        self._current = next(self.iter, None)
        if self._current is None:
            self._next_batch()
            if self.results is not None:
                self.iter = iter(self.results)
                self._current = next(self.iter, None)
            else:
                self._current = None
        return self._current

    def get(self, keys_only):
        return Model.get(\
                  Key(self.kind, \
                      self._current[self.index_col]), \
                  None if keys_only else zip(self.columns, self._current))

class Query(object):
    def __init__(self, kind, keys_only = True, **kwargs):
        if isinstance(kind, (list, tuple)):
            self.kind = (k if isinstance(k, basestring) else k.kind() for k in kind)
        else:
            assert isinstance(kind, basestring) or isinstance(kind, ModelMetaClass)
            self.kind = (kind,) if isinstance(kind, basestring) else (kind.kind(),)
        self._mm = (Model.for_name(k).modelmanager for k in self.kind)
        self.keys_only = keys_only
        self.filters = []
        self.results = None
        self.res_ix = -1
        print "__init__ self.kind %s" % list(self.kind)

    def ancestor(self, ancestor):
        print "ancestor in self.kind %s" % list(self.kind)
        self.res_ix = -1
        self.results = None
        for k in self.kind:
            if Model.for_name(k)._flat:
                logger.debug("Cannot do ancestor queries on flat model %s. Ignoring request to do so anyway", self.kind)
                return
        assert (ancestor is None) or isinstance(ancestor, basestring) or \
            isinstance(ancestor, Model) or isinstance(ancestor, Key), \
            "Must specify an ancestor object or None in Query.ancestor"
        if (isinstance(ancestor, basestring)):
            ancestor = Key(ancestor) if ancestor != "/" else "/"
        elif (isinstance(ancestor, Model)):
            ancestor = ancestor.key()
        elif not ancestor:
            ancestor = "/"
        self._ancestor = ancestor
        print "ancestor out self.kind %s" % list(self.kind)

    def _get_ancestor(self):
        return (self._ancestor().path() if self._ancestor != "/" else self._ancestor) \
            if hasattr(self, "_ancestor") \
            else None

    def filter(self, expression, value):
        print "filter in self.kind %s" % list(self.kind)
        self.res_ix = -1
        self.results = None
        if isinstance(value, Key):
            value = value.name
        elif isinstance(value, Model):
            value = value.name()
        self.filters.append((expression, value))
        print "filter out self.kind %s" % list(self.kind)

    def __iter__(self):
        print "__iter__ in self.kind %s" % list(self.kind)
        self.res_ix = 0
        self.results = [ QueryResults(self, k) for k in self.kind ]
        print "len() %s" % len(self.results)
        return self

    def next(self):
        print "res_ix %s" % self.res_ix
        print "results[res_ix] %s" % type(self.results[self.res_ix])
        result = next(self.results[self.res_ix])
        while result is None:
            self.res_ix += 1
            if self.res_ix < len(self.results):
                result = next(self.results[self.res_ix])
            else:
                raise StopIteration
        return self.results[self.res_ix].get(self.keys_only)

    def count(self):
        ret = 0
        for mm in self._mm:
            ret += mm.count(self._get_ancestor(), self.filters)
        return ret

    def delete(self):
        # FIXME: If on_delete is not defined for the model, don't do this
        for m in self:
            m.on_delete()
        for mm in self._mm:
            return mm.delete_query(self._get_ancestor(), self.filters)

    def run(self):
        return self.__iter__()

    def get(self):
        if not self.results:
            self.results = QueryResults(self)
        result = next(self.results)
        if result:
            return Model.get(Key(self.results.kind, result[0]))

    def fetch(self):
        results = [ r for r in self ]
        ret = results[0] \
            if len(results) == 1 \
            else (results \
                    if len(results) \
                    else None)
        logging.debug("Query(%s, %s, %s).fetch(): %s", self.kind, self.filters, self._ancestor if hasattr(self, "_ancestor") else None, ret)
        return ret

class QueryProperty(object):
    def __init__(self, name, foreign_kind, foreign_key, private = True, serialize = False, verbose_name = None):
        self.name = name
        self.fk_kind = foreign_kind if isinstance(foreign_kind, ModelMetaClass) else Model.for_name(foreign_kind)
        self.fk = foreign_key
        self.verbose_name = verbose_name if verbose_name else name
        self.serialize = serialize
        self.private = private

    def _get_query(self, instance):
        q = Query(self.fk_kind)
        q.filter('"%s" = ' % self.fk, instance)
        return q

    def __get__(self, instance, owner):
        if not instance:
            return self
        return self._get_query(instance)

    def __set__(self, instance, value):
        raise AttributeError("Cannot set Query Property")

    def __delete__(self, instance):
        return NotImplemented

    def from_json_value(self, instance, values):
        pass

    def to_json_value(self, instance, values):
        values[self.name] = [obj.to_dict() if self.serialize else obj.id() for obj in self._get_query(instance)]

class StringProperty(ModelProperty):
    datatype = str
    sqltype = "TEXT"

class TextProperty(StringProperty):
    pass

class PasswordProperty(StringProperty):
    def __init__(self, *args, **kwargs):
        super(PasswordProperty, self).__init__(*args, **kwargs)
        self.private = True

    def _on_store(self, instance):
        value = self.__get__(instance, instance.__class__)
        self.__set__(instance, self.hash(value))

    @classmethod
    def hash(cls, password):
        return password if password and password.startswith("sha://") else "sha://%s" % sha.sha(password if password else "").hexdigest()

class JSONProperty(ModelProperty):
    datatype = dict
    sqltype = "TEXT"

    def _initial_value(self):
        return {}

class ListProperty(ModelProperty):
    datatype = list
    sqltype = "TEXT"

    def _initial_value(self):
        return []

class IntegerProperty(ModelProperty):
    datatype = int
    sqltype = "INTEGER"

class FloatProperty(ModelProperty):
    datatype = float
    sqltype = "DOUBLE PRECISION"

class BooleanProperty(ModelProperty):
    datatype = bool
    sqltype = "BOOLEAN"

class DateTimeProperty(ModelProperty):
    datatype = datetime.datetime
    sqltype = "TIMESTAMP WITHOUT TIME ZONE"

    def __init__(self, *args, **kwargs):
        super(DateTimeProperty, self).__init__(*args, **kwargs)
        self.auto_now = kwargs.get("auto_now", False)
        self.auto_now_add = kwargs.get("auto_now_add", False)

    def _on_insert(self, instance):
        if self.auto_now_add and (self.__get__(instance, instance.__class__) is None):
            self.__set__(instance, self.now())

    def _on_store(self, instance):
        if self.auto_now:
            self.__set__(instance, self.now())

    def now(self):
        return datetime.datetime.now()

class DateProperty(DateTimeProperty):
    datatype = datetime.date
    sqltype = "DATE"

    def now(self):
        return datetime.date.today()

class TimeProperty(DateTimeProperty):
    datatype = datetime.time
    sqltype = "TIME"

    def now(self):
        dt = datetime.datetime.now()
        return datetime.time(dt.hour, dt.minute, dt.second, dt.microsecond)

class ReferenceConverter(PropertyConverter):
    def __init__(self, reference_class, serialize):
        self.reference_class = reference_class
        self.serialize = serialize

    def convert(self, value):
        return Model.get(value)

    def to_sqlvalue(self, value):
        if value is None:
            return None
        else:
            assert isinstance(value, Model)
            k = value.key()
            return k.name if self.reference_class else str(k)

    def from_sqlvalue(self, sqlvalue):
        return Model.get(Key(self.reference_class, sqlvalue) if self.reference_class else Key(sqlvalue))

    def to_jsonvalue(self, value):
        return value.to_dict() if self.serialize else value.id()

    def from_jsonvalue(self, value):
        clazz = self.reference_class
        if isinstance(value, basestring):
            value = clazz.get(value) if clazz else Model.get(value)
        elif isinstance(value, dict) and ("key" in value):
            value = clazz.get(value["key"])
        elif not isinstance(value, clazz):
            assert 0, "Cannot update ReferenceProperty to %s (wrong type %s)" % (value, str(type(value)))
        return value

class ReferenceProperty(ModelProperty):
    datatype = Model
    sqltype = "TEXT"

    def __init__(self, *args, **kwargs):
        super(ReferenceProperty, self).__init__(*args, **kwargs)
        self.reference_class = args[0] \
            if args \
            else kwargs.get("reference_class")
        if self.reference_class and isinstance(self.reference_class, basestring):
            self.reference_class = Model.for_name(self.reference_class)
        assert not self.reference_class or isinstance(self.reference_class, ModelMetaClass)
        self.collection_name = kwargs.get("collection_name")
        self.collection_verbose_name = kwargs.get("collection_verbose_name")
        self.serialize = kwargs.get("serialize", True)
        self.collection_serialize = kwargs.get("collection_serialize", False)
        self.collection_private = kwargs.get("collection_private", True)
        self.converter = ReferenceConverter(self.reference_class, self.serialize)

    def set_kind(self, kind):
        super(ReferenceProperty, self).set_kind(kind)
        if not self.collection_name:
            self.collection_name = kind.lower() + "_set"
        if not self.collection_verbose_name:
            self.collection_verbose_name = kind.title()
        if self.reference_class:
            k = Model.for_name(kind)
            qp = QueryProperty(self.collection_name, k, self.name, self.collection_private, self.collection_serialize, self.collection_verbose_name)
            setattr(self.reference_class, self.collection_name, qp)
            self.reference_class._query_properties[self.collection_name] = qp

class SelfReferenceProperty(ReferenceProperty):
    def set_kind(self, kind):
        self.reference_class = Model.for_name(kind)
        super(SelfReferenceProperty, self).set_kind(kind)
        self.converter = ReferenceConverter(self.reference_class, self.serialize)

if __name__ == "__main__":

    with Tx.begin():
        class Test(Model):
            testname = TextProperty(required = True, is_label = True)
            value = IntegerProperty(default = 12)

        jan = Test(testname = "Jan", value = "42")
        assert jan.id() is None
        assert jan.testname == "Jan"
        assert jan.value == 42
        jan.put()
        assert jan.id() is not None, "jan.id() is still None after put()"
        x = jan.key()

    with Tx.begin():
        y = Test.get(x)
        assert y.id() == x.id
        assert y.testname == "Jan"
        assert y.value == 42
        y.value = 43
        y.put()
        assert y.value == 43

    with Tx.begin():
        tim = Test(testname = "Tim", value = 9, parent = y)
        tim.put()
        assert tim.parent().id == y.id()

        Tx.flush_cache()
        q = Query(Test)
        for t in q:
            print t.testname

        Tx.flush_cache()
        q = Query(Test, False)
        for t in q:
            print t.testname

        print Test.all().count()
        for t in Test.all():
            print t.testname

        count = Test.count()
        assert count == 2, "Expected Test.count() to return 2, but it returned %s instead" % count

        class Test2(Model):
            testname = TextProperty(required = True, is_label = True)
            value = IntegerProperty(default = 12)
        mariska = Test2(testname = "Mariska", value = 40, parent = y)
        mariska.put()

        class Test3(Model):
            testname = TextProperty(required = True, is_label = True)
            value = IntegerProperty(default = 12)
        jeroen = Test3(testname = "Jeroen", value = 44, parent = y)
        jeroen.put()

        print ">>> Test, Test2, Test3 with ancestor"
        q = Query((Test, Test2, Test3), False, ancestor = y)
        for t in q:
            print t.testname


        print ">>> Test2, Test3 with ancestor"
        q = Query((Test2, Test3), False, ancestor = y)
        for t in q:
            print t.testname

        print "<<<"



        class RefTest(Model):
            refname = TextProperty(required = True, is_key = True)
            ref = ReferenceProperty(Test)

        print ">>", jan, jan.id()
        r = RefTest(refname = "Jan", ref = jan)
        print "-->", r.refname, r.ref
        r.put()

        q = Query(Test)
        q.ancestor("/")
        for t in q:
            print t

        q = Query(Test)
        q.ancestor(y)
        for t in q:
            print t

        q = Query(Test)
        q.filter("value = ", 9)
        q.get()

        q = Query(Test)
        q.ancestor(y)
        q.filter("testname = ", 'Tim')
        q.filter("value < ", 10)
        for t in q:
            print t

        q = Query(RefTest)
        q.filter("ref = ", y)
        for t in q:
            print t

        y.reftest_set.run()

        class SelfRefTest(Model):
            selfrefname = TextProperty(key = True, required = True)
            ref = SelfReferenceProperty(collection_name = "loves")

        luc = SelfRefTest(selfrefname = "Luc")
        luc.put()

        schapie = SelfRefTest(selfrefname = "Schapie", ref = luc)
        schapie.put()
        print schapie.to_dict()

        for s in luc.loves:
            print s

        luc.ref = schapie
        luc.put()
        print schapie.to_dict()
        print luc.to_dict()
