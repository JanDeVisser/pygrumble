# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$19-Jan-2013 11:19:59 AM$"

import base64
import datetime
import json
import os
import os.path
import threading
import uuid

import json_util
import pgsql


class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class PropertyRequired(Error):
    """Raised when no value is specified for a required property"""
    def __init__(self, propname):
        self.propname = propname

    def __str__(self):
        return "Property %s requires a value" % (self.propname, )

class InvalidChoice(Error):
    """Raised when a value is specified for a property that is not in the
    property's <tt>choices</tt> list"""
    def __init__(self, propname, value):
        self.propname = propname
        self.value = value

    def __str__(self):
        return "Value %s is invalid for property %s" % (self.value, self.propname)

class ObjectDoesNotExist(Error):
    """Raised when an object is requested that does not exist"""
    def __init__(self, cls, id):
        self.cls = cls
        self.id = id

    def __str__(self):
        return "Model %s:%s does not exist" % (self.cls.__name__, self.id)

def read_file(fname):
    try:
        dirname = os.path.dirname(__file__)
        filename = "%s/%s" % (dirname, fname)
        fp = open(filename, "rb")
    except IOError as e:
        #print "IOError reading config file %s: %s" % (filename, e.strerror)
        return None
    else:
        with fp:
            return fp.read()

class Config(object):
    @classmethod
    def read_all_configs(cls):
        dirname = os.path.dirname(__file__)
        for f in os.listdir("%s/conf" % dirname):
            if f.endswith(".json"):
                (section, dot, ext) = f.partition(".")
                datastr = read_file("conf/" + section + ".json")
                if datastr:
                    config = json.loads(datastr) if datastr else {}
                    setattr(cls, section, config)

Config.read_all_configs()

class Tx(object):
    _tl = threading.local()

    def __init__(self, role):
        self.role = role
        self.cursors = []
        self.cache = {}
        self.active = True
        self.count = 0
        self._connect()
        Tx._tl.tx = self

    def _connect(self):
        config = Config.database
        assert self.role in config["postgresql"], "Config: No %s role in postgresql section of conf/database.json" % self.role
        assert "user_id" in config["postgresql"][self.role] and "password" in config["postgresql"][self.role], \
            "Config: %s role is missing user_id or password in postgresql section of conf/database.json" % self.role
        pgsql_conf = config["postgresql"]
        dsn = "user=" + pgsql_conf[self.role]["user_id"] + \
            " password=" + pgsql_conf[self.role]["password"]
        if "database" in pgsql_conf:
            dsn += " dbname=" + pgsql_conf["database"]
        if "host" in pgsql_conf:
            dsn += " host=" + pgsql_conf["host"]
        print "Connecting with role", self.role, "DSN", dsn
        self.conn = pgsql.Connection.get(dsn)

    @classmethod
    def begin(cls, role = "user"):
        return cls._tl.tx if hasattr(cls._tl, "tx") else Tx(role)

    @classmethod
    def get(cls):
        return cls._tl.tx if hasattr(cls._tl, "tx") else None

    def __enter__(self):
        self.count += 1
        #print "__enter__", self.role, self.count
        return self

    def __exit__(self, exception_type, exception_value, trace):
        #print "__exit__", self.role, self.count
        self.count -= 1
        if exception_type:
            print "Exception: ", exception_type, exception_value, trace
        if not self.count:
            try:
                self._end_tx()
            except Exception, exc:
                print exc.__class__.__name__, exc
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

def _init_schema():
    config = Config.database
    pgsql = config["postgresql"]
    if pgsql["wipe_database"]:
        raise NotImplemented
    if pgsql["wipe_schema"]:
        with Tx.begin("admin") as tx:
            cur = tx.get_cursor()
            try:
                cur.execute('DROP SCHEMA IF EXISTS "' + pgsql["schema"] + '" CASCADE')
                cur.execute('CREATE SCHEMA "' + pgsql["schema"] + '" AUTHORIZATION ' + pgsql["user"]["user_id"])
            finally:
                tx.close_cursor(cur)

_init_schema()

class ColumnDefinition(object):
    def __init__(self, name, data_type, required, defval, indexed):
        self.name = name
        self.data_type = data_type
        self.required = required
        self.defval = defval
        self.indexed = indexed

class ModelManager(object):
    modelconfig = Config.model
    models = modelconfig.get("model", {})
    def_recon_policy = modelconfig.get("reconcile", "all")

    def __init__(self, name, columns = None, kind = None):
        self.my_config = self.models.get(name, {})
        self.name = name
        self.schema = Config.database["postgresql"]["schema"]  \
            if "schema" in Config.database["postgresql"] \
            else None
        self.tableprefix = '"' + Config.database["postgresql"]["schema"] + '".' \
            if "schema" in Config.database["postgresql"] \
            else ""
        self.table = name
        self.tablename = self.tableprefix + '"' + name + '"'
        self.columns = columns
        self.kind = kind

    def set_tablename(self, tablename):
        self.table = tablename
        self.tablename = self.tableprefix + '"' + tablename + '"'

    def set_columns(self, columns):
        self.columns = columns

    def get_properties(self, key):
        if key.id:
            searchcol = 'id'
            searchval = key.id
        else:
            searchcol = 'key_name'
            searchval = key.name
        ret = None
        with Tx.begin() as tx:
            cur = tx.get_cursor()
            cols = ['id', 'key_name', 'ancestors', 'parent'] + self.columns.keys()
            sql = "SELECT "
            prev = None
            for colname in cols:
                if prev:
                    sql += ', '
                sql += '"' + colname + '"'
                prev = colname
            sql += ' FROM ' + self.tablename + ' WHERE "' + searchcol + '" = %s'
            cur.execute(sql, (searchval, ))
            values = cur.fetchone()
            if values:
                ret = zip(cols, values)
        return ret

    def set_properties(self, insert, key, ancestors, values):
        print "set_properties(%s)" % values
        ret = key.id
        with Tx.begin() as tx:
            cur = tx.get_cursor()
            if insert:
                assert key.name
                ret = base64.urlsafe_b64encode(str(key))
                v = [ret, key.name, ancestors]
                (a,sep,parent) = ancestors.rpartition("/")
                v.append(parent if parent != '' else None)
                sql = 'INSERT INTO ' + self.tablename + ' ( "id", "key_name", "ancestors", "parent"'
                for colname in values:
                    sql += ', "' + colname + '"'
                sql += ' ) VALUES ( %s, %s, %s, %s'
                for colname in values:
                    sql += ', %s'
                    v.append(values[colname])
                sql += ' )'
            else:
                assert key.id
                v = []
                sql = 'UPDATE ' + self.tablename + ' SET '
                prev = None
                for colname in values:
                    if prev:
                        sql += ','
                    sql += '"' + colname + '" = %s'
                    v.append(values[colname])
                    prev = colname
                sql += ' WHERE "id" = %s'
                v.append(key.id)
            cur.execute(sql, v)
        return ret

    def delete(self, id):
        with Tx.begin() as tx:
            cur = tx.get_cursor()
            sql = "DELETE FROM %s WHERE id = %%s" % self.tablename
            cur.execute(sql, (id, ))

    def query(self, ancestor, filters, what = "key_name"):
        if what == "columns":
            cols = ['id', 'key_name', 'ancestors', 'parent'] + self.columns.keys()
            collist = ""
            for colname in cols:
                if len(collist):
                    collist += ', '
                collist += '"' + colname + '"'
        else:
            collist = what
            cols = (what,)
        v = []
        sql = 'SELECT %s FROM %s' % (collist, self.tablename)
        glue = ' WHERE '
        if ancestor:
            glue = ' AND '
            if ancestor != "/":
                sql += ' WHERE "ancestors" LIKE %s'
                v.append(ancestor + "%")
            else:
                sql += ' WHERE "ancestors" = \'/\''
        for (expression, value) in filters:
            sql += glue
            glue = " AND "
            sql += expression + " %s"
            v.append(value)
        tx = Tx.get()
        assert tx, "ModelManager.query: no transaction active"
        cur = tx.get_cursor()
        cur.execute(sql, v)
        return (cur, cols)

    def _next_batch(self, cur):
        ret = cur.fetchmany()
        if len(ret) < cur.arraysize:
            tx = Tx.get()
            assert tx, "ModelManager.query: no transaction active"
            tx.close_cursor(cur)
        return ret

    def count(self, ancestor, filters):
        (cur, ignored) = self.query(ancestor, filters, 'COUNT(*)')
        ret = cur.fetchone()[0]
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
                else: # _recon is 'all' or 'add'
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
        cur.execute('CREATE TABLE %s ( "id" TEXT NOT NULL PRIMARY KEY, "key_name" TEXT NOT NULL UNIQUE, "ancestors" TEXT, "parent" TEXT NULL )' % (self.tablename, ))
        cur.execute('CREATE UNIQUE INDEX "%s__ancestors" ON %s ( "ancestors", "id" )' % (self.table, self.tablename))
        cur.execute('CREATE UNIQUE INDEX "%s__parent" ON %s ( "parent", "id" )' % (self.table, self.tablename))
        self.update_table(cur)

    def update_table(self, cur):
        sql = """SELECT column_name, column_default, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = %s AND column_name NOT IN ('id', 'key_name', 'ancestors', 'parent')"""
        v = [ self.table ]
        if self.schema:
            sql += ' AND table_schema = %s'
            v.append(self.schema)
        cur.execute(sql, v)
        for (colname, defval, is_nullable, data_type) in cur:
            column = self.columns[colname]
            if column:
                if data_type.lower() != column.data_type.lower():
                    cur.execute('ALTER TABLE ' + self.tablename + ' DROP COLUMN "' + colname + '"')
                    # We're not removing the column from the dict -
                    # we'll re-add the column when we add 'new' columns
                else:
                    if self._recon == "all":
                        alter = ""
                        vars = []
                        if column.required != (is_nullable == 'NO'):
                            alter = " NOT NULL" if column.required else " NULL"
                        if column.defval != defval:
                            alter += " DEFAULT %s"
                            vars.append(column.defval)
                        if alter != "":
                            cur.execute('ALTER TABLE %s ALTER COLUMN "%s" %s' % ( self.tablename, colname, alter ), vars)
                    del self.columns[colname]
        for (colname, column) in self.columns.items():
            vars = []
            sql = 'ALTER TABLE ' + self.tablename + ' ADD COLUMN "' + colname + '" ' + column.data_type
            if column.required:
                sql += " NOT NULL"
            if column.defval:
                sql += " DEFAULT %s"
                vars.append(column.defval)
            cur.execute(sql, vars)
            if column.indexed:
                cur.execute('CREATE UNIQUE INDEX "%s_%s" ON %s ( "%s", "id" )' % (self.table, colname, self.tablename, colname))

    modelmanagers_byname = {}
    @classmethod
    def for_name(cls, name):
        if name in cls.modelmanagers_byname:
            ret = cls.modelmanagers_byname[name]
        else:
            ret = ModelManager(name)
            cls.modelmanagers_byname[name] = ret
        return ret

class ModelProperty(object):
    def __new__(cls, *args, **kwargs):
        ret = super(ModelProperty, cls).__new__(cls)
        ret.required = kwargs["required"] if "required" in kwargs else False
        ret.default = kwargs["default"] if "default" in kwargs else None
        ret.column_name = kwargs["column_name"] if "column_name" in kwargs else None
        ret.verbose_name = kwargs["verbose_name"] if "verbose_name" in kwargs else None
        ret.private = kwargs["private"] if "private" in kwargs else False
        ret.transient = kwargs["transient"] if "transient" in kwargs else False
        ret.is_label = kwargs["is_label"] if "is_label" in kwargs else False
        ret.is_key = kwargs["is_key"] if "is_key" in kwargs else False
        ret.indexed = kwargs["indexed"] if "indexed" in kwargs else False
        ret.validator = kwargs["validator"] if "validator" in kwargs else None
        assert (ret.validator is None) or callable(ret.validator), "Validator %s must be function, not %s" % (str(ret.validator), type(ret.validator))
        ret.choices = kwargs["choices"] if "choices" in kwargs else None
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
        return ColumnDefinition(self.column_name, self.sqltype, self.required, self.default, self.indexed)

    def _on_insert(self, value):
        if not value and self.default:
            return self.default
        else:
            return value

    def _initial_value(self):
        return self.default

    def __get__(self, instance, owner):
        if not instance:
            return self
        instance._load()
        return instance._values[self.name] if self.name in instance._values else None

    def __set__(self, instance, value):
        instance._load()
        instance._values[self.name] = self.convert(value) if value is not None else None

    def __delete__(self, instance):
        return NotImplemented

    def convert(self, value):
        return self.datatype(value)

    def to_sqlvalue(self, value):
        return value

    def from_sqlvalue(self, sqlvalue):
        return sqlvalue

    def from_json_value(self, json_value):
        return json_value

    def to_json_value(self, value):
        return value

    def _on_store(self, value):
        return value

    def validate(self, value):
        if (value is None) and self.required:
            raise PropertyRequired(self.name)
        if self.choices and value not in self.choices:
            raise InvalidChoice(self.name, value)
        if self.validator:
            self.validator(value)

class ModelMetaClass(type):
    def __new__(cls, name, bases, dct):
        kind = type.__new__(cls, name, bases, dct)
        if name != 'Model':
            Model._register_class(name, kind)
            if hasattr(kind, "table_name"):
                tablename = kind.table_name
            else:
                tablename = name
                kind.table_name = name
            properties = {}
            columns = {}
            for (propname, value) in dct.items():
                if isinstance(value, ModelProperty):
                    value.set_name(propname)
                    value.set_kind(name)
                    if not value.transient:
                        columns[propname] = value.get_coldef()
                    if value.is_label:
                        assert not hasattr(kind, "label_prop"), "Can only assign one label property"
                        kind.label_prop = value
                    if value.is_key:
                        assert not hasattr(kind, "key_prop"), "Can only assign one key property"
                        kind.key_prop = value
                    properties[propname] = value
            kind._properties = properties
            kind._kind = name
            mm = ModelManager.for_name(name)
            mm.set_tablename(tablename)
            mm.set_columns(columns)
            mm.kind = kind
            mm.reconcile()
            kind.modelmanager = mm
            kind.load_template_data()
        return kind

class Model(object):
    __metaclass__ = ModelMetaClass
    classes = {}

    def __new__(cls, *args, **kwargs):
        ret = super(Model, cls).__new__(cls)
        ret._brandnew = True
        ret._set_ancestors_from_parent(kwargs["parent"] if "parent" in kwargs else None)
        ret._key_name = kwargs["key_name"] if "key_name" in kwargs else None
        ret._id = None
        ret._values = {}
        for (propname, prop) in ret._properties.items():
            setattr(ret, propname, prop._initial_value())
        for (propname, propvalue) in kwargs.items():
            if propname in ret._properties:
                setattr(ret, propname, propvalue)
        print "__new__: ", ret._values
        return ret

    def __repr__(self):
        label = None
        id = self.get_key()
        if hasattr(self, "label_prop"):
            label = getattr(self, self.label_prop)
        if id:
            s = id
            if label:
                s += " (%s)"  % label
            return "<%s: %s>" % (self.__class__.__name__ , s)
        else:
            super(self.__class__, self).__repr__()

    def get_label(self):
        return self.label_prop.name if hasattr(self, "label_prop") else str(self)

    def get_key(self):
        return self.key_prop if hasattr(self, "key_prop") else str(self.key())

    def properties(self):
        return self._properties

    def _set_ancestors_from_parent(self, parent):
        if parent:
            parent = Key(parent)
        assert parent is None or isinstance(parent, Key)
        self._parent = parent
        if parent:
            p = parent.get()
            self._ancestors = p.path()
        else:
            self._ancestors = "/"

    def _set_ancestors(self, ancestors, parent):
        if ancestors == "/":
            self._parent = None
            self._ancestors = "/"
        elif isinstance(ancestors, basestring):
            self._ancestors = ancestors
            (a,sep,p) = ancestors.rpartition("/")
            assert p == str(parent)
            self._parent = Key(p)

    def _populate(self, values):
        print "_populate(%s)" % values
        if values:
            self._values = {}
            for (name, value) in values:
                if name == "ancestors":
                    ancestors = value
                elif name == "parent":
                    parent = value
                elif name == "id":
                    self._id = value
                elif name == "key_name":
                    self._key_name = value
                else:
                    self._values[name] = self._properties[name].from_sqlvalue(value)
            self._set_ancestors(ancestors, parent)
            self._exists = True
        else:
            self._exists = False

    def _load(self):
        if (not hasattr(self, "_values") or not self._values) and (self._id or self._key_name):
            self._populate(self.modelmanager.get_properties(self.key()))

    def _store(self):
        self._load()
        if not self._key_name:
            if hasattr(self, "key_prop"):
                self._key_name = "%s/%s" % (parent(), getattr(self, "key_prop"))
            else:
                self._key_name = uuid.uuid1().hex
            self._id = None
        if hasattr(self, "_brandnew"):
            for (name, prop) in self._properties.items():
                self._values[name] = prop._on_insert(self._values[name] if name in self._values else None)
            self.initialize()
        for (name, prop) in self._properties.items():
            self._values[name] = prop._on_store(self._values[name])
        self.on_store()
        self.validate()
        values = {}
        for (name, value) in self._values.items():
            values[name] = self._properties[name].to_sqlvalue(value)
        self._id = self.modelmanager.set_properties(hasattr(self, "_brandnew"), self.key(), self._ancestors, values)
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
            prop.validate(self._values[name])

    def id(self):
        return self._id

    def name(self):
        return self._key_name

    def parent(self):
        self._load()
        return self._parent

    def key(self):
        return Key(self) if (self._id or self._key_name) else None

    def path(self):
        self._load()
        return (self._ancestors if self._ancestors != "/" else "") + "/" + str(self.key())

    def pathlist(self):
        pl = self.path().split("/")
        del pl[0] # First element is "/" because the path starts with a "/"
        return [Model.get(k) for k in pl]

    def root(self):
        pl = self.pathlist()
        return pl[0] if pl else self

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
        ret = { "key": str(self.key()) }
        for b in self.__class__.__bases__:
            if hasattr(b, "_to_dict") and callable(b._to_dict):
                b._to_dict(self, ret)
        for name, prop in self.properties().items():
            if prop.private:
                continue
            if hasattr(self, "to_dict_" + name) and callable(getattr(self, "to_dict_" + name)):
                getattr(self, "to_dict_" + name)(ret)
            else:
                val = prop.from_json_value(getattr(self, name))
                ret[name] = val
        hasattr(self, "sub_to_dict") and callable(self.sub_to_dict) and self.sub_to_dict(ret)
        return ret

    def _update(self, d):
        pass

    def update(self, descriptor):
        for b in self.__class__.__bases__:
            if hasattr(b, "_update") and callable(b._update):
                b._update(self, descriptor)
        for name, prop in self.properties().items():
            if (name not in descriptor) or prop.private:
                continue
            newval = descriptor[name]
            print "Updating %s.%s to %s" % (self.__class__.__name__, name, newval)
            newval = prop.from_json_value(newval)
            if hasattr(self, "update_" + name) and callable(getattr(self, "update_" + name)):
                getattr(self, "update_" + name)(newval, descriptor)
            else:
                curval = getattr(self, name)
                if newval != curval:
                    setattr(self, name, newval)
        self.put()
        hasattr(self, "sub_update") and callable(self.sub_update) and self.sub_update(descriptor)
        self.put()
	return self.to_dict()

    @classmethod
    def kind(cls):
        return cls._kind

    @classmethod
    def for_name(cls, name):
        return Model.classes[name] if name in Model.classes else None

    @classmethod
    def _register_class(cls, name, modelclass):
        Model.classes[name] = modelclass

    @classmethod
    def get(cls, key, values = None):
        k = Key(key)
        if cls != Model:
            ret = Tx.get_from_cache(k)
            if not ret:
                ret = super(Model, cls).__new__(cls)
                assert (k.kind == cls.kind()) or not k.kind
                ret._id = k.id
                ret._key_name = k.name
                if values:
                    ret._populate(values)
            else:
                #print "%s.get - Cache hit" % cls.__name__
                pass
        else:
            assert k.kind
            return Model.for_name(k.kind).get(k, values)
        return ret

    @classmethod
    def query(cls, *args, **kwargs):
        assert not len(args) % 2, "Must specify a value for every filter"
        assert cls != Model, "Cannot query on unconstrained Model class"
        q = Query(cls, kwargs.get("keys_only", True))
        if "ancestor" in kwargs:
            q.ancestor(kwargs["ancestor"])
        ix = 0
        while ix < len(args):
            q.filter(args[ix], args[ix+1])
            ix += 2
        return q.fetch()

    @classmethod
    def create(cls, descriptor = None, parent = None):
        if descriptor is None:
            descriptor = {}
        obj = None
        kwargs = { "parent": parent }
        kwargs.update(descriptor)
        k = cls.get_new_key(descriptor, parent)
        if k:
            kwargs["key_name"] = k
        obj = cls(**kwargs)
        obj.update(descriptor)
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
        print "load_template_data(%s)" % fname
        datastr = read_file(fname)
        if datastr:
            with Tx.begin():
                if cls.all(keys_only = True).count() > 0:
                    print "Template data for class %s already loaded" % cls.__name__
                else:
                    print "Loading template data for class %s from %s" % (cls.__name__, fname)
                    data = json.loads(datastr)
                    print "version %s" % data["version"]
                    for d in data[cname]:
                        print "Creating %s with %s" % (cls.__name__, d)
                        cls.create(d)

def delete(model):
    if not hasattr(model, "_brandnew") and model.exists():
        model.on_delete()
        mm = model.modelmanager
        mm.delete(model.id())
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
            if isinstance(value, basestring):
                self._assign(value)
            elif isinstance(value, dict):
                if "id" in dict:
                    self.__init__(dict[id])
                else:
                    self.__init__(dict["kind"], dict["name"])
            elif isinstance(value, Model):
                self.kind = value.kind()
                self.id = value.id()
                self.name = value.name()
            elif isinstance(value, Key):
                self.kind = value.kind
                self.id = value.id
                self.name = value.name
        elif len(args) == 2:
            kind = args[0]
            assert isinstance(kind, basestring) or isinstance(kind, ModelMetaClass)
            assert isinstance(args[1], basestring)
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
        return (self.kind + ":" + self.name) if hasattr(self, "name") else self.id

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

class Query(object):
    def __init__(self, kind, keys_only = True, **kwargs):
        assert isinstance(kind, basestring) or isinstance(kind, ModelMetaClass)
        self.kind = kind if isinstance(kind, basestring) else kind.kind()
        self._mm = ModelManager.for_name(self.kind)
        self.keys_only = keys_only
        self.filters = []

    def ancestor(self, ancestor):
        assert (ancestor is None) or isinstance(ancestor, basestring) or \
            isinstance(ancestor, Model) or isinstance(ancestor, Key), \
            "Must specify an ancestor object in Query.ancestor"
        if hasattr(self, "results"):
            del self.results
        if (isinstance(ancestor, basestring)):
            ancestor = Key(ancestor) if ancestor != "/" else "/"
        elif (isinstance(ancestor, Model)):
            ancestor = ancestor.key()
        elif not ancestor:
            ancestor = "/"
        self._ancestor = ancestor

    def _get_ancestor(self):
        return (self._ancestor().path() if self._ancestor != "/" else self._ancestor) \
            if hasattr(self, "_ancestor") \
            else None

    def filter(self, expression, value):
        if hasattr(self, "results"):
            del self.results
        if isinstance(value, Key):
            value = value.id
        elif isinstance(value, Model):
            value = value.id()
        self.filters.append((expression, value))

    def execute(self):
        (self.cur, self.columns) = self._mm.query(self._get_ancestor(), self.filters, "key_name" if self.keys_only else "columns")
        self._next_batch()

    def _next_batch(self):
        self.results = self._mm._next_batch(self.cur)

    def __iter__(self):
        if hasattr(self, "results"):
            del self.results
        if hasattr(self, "iter"):
            del self.iter
        return self

    def next(self):
        if not hasattr(self, "results"):
            self.execute()
            self.iter = iter(self.results)
        result = next(self.iter, None)
        if result == None:
            self._next_batch()
            self.iter = iter(self.results)
            result = next(self.iter)
        return Model.get(Key(self.kind, result[0]), None if self.keys_only else zip(self.columns, result))

    def count(self):
        return self._mm.count(self._get_ancestor(), self.filters)

    def run(self):
        return self.__iter__()

    def get(self):
        if not hasattr(self, "results"):
            self.execute()
        if self.results:
            result = self.results[0]
            return Model.get(Key(self.kind, result[0]))

    def fetch(self):
        if not hasattr(self, "results"):
            self.execute()
        if self.results:
            results = [ r for r in self ]
            ret = results[0] \
                if len(results) == 1 \
                else (results \
                        if len(results) \
                        else None)
            print "Query(%s, %s, %s).fetch(): %s" % (self.kind, self.filters, self._ancestor if hasattr(self, "_ancestor") else None, ret)
            return ret

class QueryProperty(object):
    def __init__(self, name, foreign_kind, foreign_key, verbose_name = None):
        self.name = name
        self.fk_kind = foreign_kind if isinstance(foreign_kind, ModelMetaClass) else Model.for_name(foreign_kind)
        self.fk = foreign_key
        self.verbose_name = verbose_name if verbose_name else None

    def __get__(self, instance, owner):
        if not instance:
            return self
        q = Query(self.fk_kind)
        q.filter(self.fk + " = ", instance)
        return q

    def __set__(self, instance, value):
        raise AttributeError("Cannot set Query Property")

    def __delete__(self, instance):
        return NotImplemented

class StringProperty(ModelProperty):
    datatype = str
    sqltype = "TEXT"

class TextProperty(StringProperty):
    pass

class JSONProperty(ModelProperty):
    datatype = dict
    sqltype = "TEXT"

    def convert(self, value):
        if isinstance(value, dict):
            return dict(value)
        elif value is None:
            return {}
        else:
            return json.loads(str(value))

    def _initial_value(self):
        return {}

    def to_sqlvalue(self, value):
        return json.dumps(value if value else {})

    def from_sqlvalue(self, sqlvalue):
        return json.loads(sqlvalue) if sqlvalue else {}

    def to_json_value(self, value):
        assert value is not None, "JSONProperty.to_json_value(): value should not be None"
        return dict(value)

    def from_json_value(self, value):
        return dict(value) if value is not None else {}

class ListProperty(ModelProperty):
    datatype = list
    sqltype = "TEXT"

    def convert(self, value):
        if value is None:
            return []
        else:
            try:
                return list(value)
            except:
                ret = json.loads(str.value)
                assert isinstance(ret,list), "Value %s for ListProperty cannot be converted to list" % value
                return ret

    def _initial_value(self):
        return []

    def to_sqlvalue(self, value):
        return json.dumps(value if value else [])

    def from_sqlvalue(self, sqlvalue):
        return json.loads(sqlvalue) if sqlvalue else []

    def to_json_value(self, value):
        assert value is not None, "JSONProperty.to_json_value(): value should not be None"
        return list(value)

    def from_json_value(self, value):
        return list(value) if value is not None else []

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
    sqltype = "TIMESTAMP"

    def __init__(self, *args, **kwargs):
        super(DateTimeProperty, self).__init__(*args, **kwargs)
        self.auto_now = kwargs["auto_now"] if "auto_now" in kwargs else False
        self.auto_now_add = kwargs["auto_now_add"] if "auto_now_add" in kwargs else False

    def to_json_value(self, value):
        return json_util.datetime_to_dict(value)

    def from_json_value(self, value):
        return json_util.dict_to_datetime(value) if isinstance(value, dict) else value

    def _on_insert(self, value):
        if self.auto_now_add and (value is None):
            return self.now()
        else:
            return value

    def _on_store(self, value):
        if self.auto_now:
            return self.now()
        else:
            return value

    def now(self):
        return datetime.datetime.now()

class DateProperty(DateTimeProperty):
    datatype = datetime.date
    sqltype = "DATE"

    def to_json_value(self, value):
        return json_util.date_to_dict(value)

    def from_json_value(self, value):
        return json_util.dict_to_date(value) if isinstance(value, dict) else value

    def now(self):
        return datetime.date.today()

class TimeProperty(DateTimeProperty):
    datatype = datetime.time
    sqltype = "TIME"

    def to_json_value(self, value):
        return json_util.time_to_dict(value)

    def from_json_value(self, value):
        return json_util.dict_to_time(value) if isinstance(value, dict) else value

    def now(self):
        dt = datetime.datetime.now()
        return datetime.time(dt.hour, dt.minute, dt.second, dt.microsecond)

class ReferenceProperty(ModelProperty):
    datatype = Model
    sqltype = "TEXT"

    def __init__(self, *args, **kwargs):
        super(ReferenceProperty, self).__init__(*args, **kwargs)
        self.reference_class = args[0] \
            if args \
            else (kwargs["reference_class"] if "reference_class" in kwargs else None)
        if self.reference_class and isinstance(self.reference_class, basestring):
            self.reference_class = Model.for_name(self.reference_class)
        self.collection_name = kwargs["collection_name"] if "collection_name" in kwargs else None
        self.collection_verbose_name = kwargs["collection_verbose_name"] if "collection_verbose_name" in kwargs else None
        assert not self.reference_class or isinstance(self.reference_class, ModelMetaClass)

    def set_kind(self, kind):
        super(ReferenceProperty, self).set_kind(kind)
        if not self.collection_name:
            self.collection_name = kind.lower() + "_set"
        if not self.collection_verbose_name:
            self.collection_verbose_name = kind.title()
        k = Model.for_name(kind)
        qp = QueryProperty(self.collection_name, k, self.name, self.collection_verbose_name)
        setattr(self.reference_class, self.collection_name, qp)

    def convert(self, value):
        return Model.get(value)

    def to_sqlvalue(self, value):
        if value is None:
            return None
        else:
            assert isinstance(value, Model)
            k = value.key()
            return k.id if self.reference_class else str(k)

    def from_sqlvalue(self, sqlvalue):
        return Model.get(Key(self.reference_class, sqlvalue) if self.reference_class else Key(sqlvalue))

    def to_json_value(self, value):
        return value.to_dict()

    def from_json_value(self, value):
        clazz = prop.reference_class
        if isinstance(value, basestring):
            value = clazz.get(newval) if clazz else Model.get(newval)
        elif isinstance(value, dict) and ("key" in value):
            value = clazz.get(value["key"])
        elif not isinstance(newval, clazz):
            assert 0, "Cannot update %s.% to %s (wrong type %s)" % (self.__class__.__name__, name, value, str(type(newval)))
        return value

class SelfReferenceProperty(ReferenceProperty):
    def set_kind(self, kind):
        self.reference_class = Model.for_name(kind)
        super(SelfReferenceProperty, self).set_kind(kind)

if __name__ == "__main__":

    with Tx.begin():
        class Test(Model):
            label_prop = "testname"
            testname = TextProperty(required = True)
            value = IntegerProperty(default = 12)

        jan = Test(testname = "Jan", value = "42")
        print "++", jan.id(), jan.testname, jan.value
        jan.put()
        print "+++", jan.id()

        x = jan.key()

        y = Test.get(x)
        print y.testname, y.value

        tim = Test(testname = "Tim", value = 9, parent = y)
        tim.put()
        print tim.parent()

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

        class RefTest(Model):
            refname = TextProperty(required = True)
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

        for s in luc.loves:
            print s

