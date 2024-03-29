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

import datetime
import hashlib
import json
import re

import gripe
import grumble.converter
import grumble.errors
import grumble.schema

logger = gripe.get_logger(__name__)


class Validator(object):
    def property(self, prop = None):
        if prop:
            self.prop = prop
            if hasattr(self, "updateProperty") and \
                    callable(self.updateProperty):
                self.updateProperty(prop)
        return prop


class RequiredValidator(Validator):
    def __call__(self, instance, value):
        if value is None:
            raise grumble.errors.PropertyRequired(self.prop.name)


class ChoicesValidator(Validator, set):
    def __init__(self, choices = None):
        if choices:
            if isinstance(choices, (list, set, tuple, dict)):
                for c in choices:
                    self.add(c)
            else:
                self.add(choices)

    def __call__(self, instance, value):
        if isinstance(value, (list, tuple)):
            for v in value:
                self(instance, v)
        else:
            if (value is not None) and (value not in self):
                raise grumble.errors.InvalidChoice(self.prop.name, value)


class RangeValidator(Validator):
    def __init__(self, minval = None, maxval = None):
        self._minval = minval if minval is not None else -float("inf")
        self._maxval = maxval if maxval is not None else float("inf")
        assert self._minval < self._maxval, "Minimum value for RangeValidator must be less than maximum value"

    def __call__(self, instance, value):
        if value < self._minval or value > self._maxval:
            raise grumble.errors.OutOfRange(self.prop.name, value)


class RegExpValidator(Validator):
    def __init__(self, pat = None):
        self._pattern = None
        self.pattern(pat)

    def pattern(self, pat):
        if pat is not None:
            self._pattern = pat
        return self._pattern

    def updateProperty(self, property):
        property.config["regexp"] = self._pattern

    def __call__(self, instance, value):
        if value and not re.match(self.pattern(), value):
            raise grumble.errors.PatternNotMatched(self.prop.name, value)


class ModelProperty(object):
    property_counter = 0
    _default_validators = []

    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], ModelProperty):
            prop = args[0]
            ret = super(ModelProperty, prop.__class__).__new__(prop.__class__)
            ret.name = prop.name
            ret.column_name = prop.column_name
            ret.verbose_name = prop.verbose_name
            ret.readonly = prop.readonly
            ret.default = prop.default
            ret.private = prop.private
            ret.transient = prop.transient
            ret.required = prop.required
            ret.is_label = prop.is_label
            ret.is_key = prop.is_key
            ret.scoped = prop.scoped
            ret.indexed = prop.indexed
            ret.suffix = prop.suffix

            ret.converter = prop.converter
            ret.getvalue = prop.getvalue
            ret.setvalue = prop.setvalue
            ret.validators = []
            for v in prop.validators:
                ret.validators.append(v)
            ret.on_assign = prop.on_assign
            ret.assigned = prop.assigned

            ret.seq_nr = prop.seq_nr
            ret.config = dict(prop.config)
            ret.inherited_from = prop
        else:
            ret = super(ModelProperty, cls).__new__(cls)
            ret.config = {}
            ret.seq_nr = ModelProperty.property_counter
            ModelProperty.property_counter += 1
            ret.name = kwargs.get("name", None)
            ret.column_name = kwargs.get("column_name", cls.column_name if hasattr(cls, "column_name") else None)
            ret.verbose_name = kwargs.get("verbose_name",
                cls.verbose_name
                    if hasattr(cls, "verbose_name")
                    else ret.name)
            ret.readonly = kwargs.get("readonly", cls.readonly if hasattr(cls, "readonly") else False)
            ret.default = kwargs.get("default", cls.default if hasattr(cls, "default") else None)
            ret.private = kwargs.get("private", cls.private if hasattr(cls, "private") else False)
            ret.transient = kwargs.get("transient", cls.transient if hasattr(cls, "transient") else False)
            ret.is_label = kwargs.get("is_label", cls.is_label if hasattr(cls, "is_label") else False)
            ret.is_key = kwargs.get("is_key", cls.is_key if hasattr(cls, "is_key") else False)
            ret.scoped = kwargs.get("scoped", cls.scoped if hasattr(cls, "scoped") else False) if ret.is_key else False
            ret.indexed = kwargs.get("indexed", cls.indexed if hasattr(cls, "indexed") else False)
            ret.suffix = kwargs.get("suffix", cls.suffix if hasattr(cls, "suffix") else None)
            ret.converter = kwargs.get("converter", \
                ret.converter \
                    if hasattr(ret, "converter") \
                    else grumble.converter.Converters.get(cls.datatype, ret)
            )
            if "getvalue" in kwargs:
                ret.getvalue = kwargs.get("getvalue")
            if not hasattr(ret, "getvalue"):
                ret.getvalue = None
            if "setvalue" in kwargs:
                ret.setvalue = kwargs.get("setvalue")
            if not hasattr(ret, "setvalue"):
                ret.setvalue = None
            ret.validators = []
            ret.required = kwargs.get("required", cls.required if hasattr(cls, "required") else False)
            if ret.required:
                ret.validator(RequiredValidator())
            regexp = kwargs.get("regexp", None)
            if regexp:
                ret.validator(RegExpValidator(regexp))
            choices = kwargs.get("choices", None)
            if choices:
                ret.validator(ChoicesValidator(choices))
            minval = kwargs.get("minimum", None)
            maxval = kwargs.get("maximum", None)
            if minval is not None or maxval is not None:
                ret.validator(RangeValidator(minval, maxval))
            v = kwargs.get("validator")
            if v is not None:
                ret.validator(v)
            validators = kwargs.get("validators")
            if validators is not None:
                for v in validators:
                    ret.validator(v)
            ret.on_assign = kwargs.get("on_assign", \
                cls.on_assign \
                    if hasattr(cls, "on_assign") \
                    else None
            )
            ret.assigned = kwargs.get("assigned", \
                cls.assigned \
                    if hasattr(cls, "assigned") \
                    else None
            )
            ret.inherited_from = None
            ret.config.update(kwargs)
        return ret

    def set_name(self, name):
        self.name = name
        if not self.column_name:
            self.column_name = name
            self.config["column_name"] = self.column_name
        if not self.verbose_name:
            self.verbose_name = name.replace('_', ' ').title()
            self.config["verbose_name"] = self.verbose_name

    def set_kind(self, kind):
        self.kind = kind

    def get_coldef(self):
        ret = grumble.schema.ColumnDefinition(self.column_name, self.sqltype, self.required, self.default, self.indexed)
        ret.is_key = self.is_key
        ret.scoped = self.scoped
        return [ret]

    def validator(self, v):
        assert callable(v) or (hasattr(v, "validate") and callable(v.validate)), "Cannot add non-callable validator %s" % v
        if v is not None:
            if hasattr(v, "property") and callable(v.property):
                v.property(self)
            self.validators.append(v)
        return self

    def _on_insert(self, instance):
        value = self.__get__(instance)
        if not value and self.default:
            return self.__set__(instance, self.default)

    def _initial_value(self):
        return self.default

    def _on_store(self, value):
        pass

    def _after_store(self, value):
        pass

    def schema(self):
        ret = {
            "name": self.name, "type": self.__class__.__name__,
            "verbose_name": self.verbose_name,
            "default": self.default, "readonly": self.readonly,
            "is_key": self.is_key, "datatype": self.datatype.__name__
        }
        self._schema(ret)
        return ret;

    def _schema(self, schema):
        return schema

    def _validate(self, instance, value):
        for v in self.__class__._default_validators + self.validators:
            v(instance, value) if callable(v) else v.validate(instance, value)

    def _update_fromsql(self, instance, values):
        instance._values[self.name] = self._from_sqlvalue(values[self.column_name])

    def _values_tosql(self, instance, values):
        if not self.transient:
            values[self.column_name] = self._to_sqlvalue(self.__get__(instance))

    def _get_storedvalue(self, instance):
        instance._load()
        return instance._values[self.name] if self.name in instance._values else None

    def __get__(self, instance, owner=None):
        try:
            if not instance:
                return self
            if self.transient and hasattr(self, "getvalue"):
                ret = self.getvalue(instance)
                if ret:
                    instance._load()
                    instance._values[self.name] = ret
                return ret
            else:
                return self._get_storedvalue(instance)
        except:
            logger.exception("Exception getting property '%s'", self.name)
            raise

    def __set__(self, instance, value):
        try:
            if self.is_key and not hasattr(instance, "_brandnew"):
                return
            if self.transient and hasattr(self, "setvalue") and callable(self.setvalue):
                return self.setvalue(instance, value)
            else:
                instance._load()
                old = instance._values[self.name] if self.name in instance._values else None
                converted = self.convert(value) if value is not None else None
                if self.on_assign:
                    self.on_assign(instance, old, converted)
                instance._values[self.name] = converted
                if self.assigned:
                    self.assigned(instance, old, converted)
        except:
            logger.exception("Exception setting property '%s' to value '%s'", self.name, value)
            raise

    def __delete__(self, instance):
        return NotImplemented

    def convert(self, value):
        return self.converter.convert(value)

    def _to_sqlvalue(self, value):
        return self.converter.to_sqlvalue(value)

    def _from_sqlvalue(self, sqlvalue):
        return self.converter.from_sqlvalue(sqlvalue)

    def _from_json_value(self, value):
        try:
            return self.datatype.from_dict(value)
        except:
            try:
                return self.converter.from_jsonvalue(value)
            except:
                logger.exception("ModelProperty<%s>.from_json_value(%s [%s])", self.__class__, value, type(value))
                return value

    def _to_json_value(self, instance, value):
        try:
            return value.to_dict()
        except:
            try:
                return self.converter.to_jsonvalue(value)
            except:
                return value


def transient(property):
    property.transient = True
    return property


class CompoundProperty(object):
    _default_validators = []

    def __init__(self, *args, **kwargs):
        self.seq_nr = ModelProperty.property_counter
        ModelProperty.property_counter += 1
        self.compound = []
        for p in args:
            self.compound.append(p)
        if "name" in kwargs:
            self.set_name(kwargs["name"])
        else:
            self.name = None
        cls = self.__class__
        self.verbose_name = kwargs.get("verbose_name", cls.verbose_name if hasattr(cls, "verbose_name") else self.name)
        self.transient = kwargs.get("transient", cls.transient if hasattr(cls, "transient") else False)
        self.private = kwargs.get("private", cls.private if hasattr(cls, "private") else False)
        self.readonly = kwargs.get("readonly", cls.readonly if hasattr(cls, "readonly") else False)
        self.validators = []
        v = kwargs.get("validator")
        if v is not None:
            self.validator(v)
        validators = kwargs.get("validators")
        if validators is not None:
            for v in validators:
                self.validator(v)

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

    def schema(self):
        ret = {
            "name": self.name, "type": self.__class__.__name__,
            "verbose_name": self.verbose_name,
            "readonly": self.readonly,
            "is_key": False,
            "components": [
                prop.schema() for prop in self.compound
            ]
        }
        self._schema(ret)
        return ret;

    def _schema(self, schema):
        return schema

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

    def _after_store(self, value):
        for p in self.compound:
            p._after_store(value)

    def _validate(self, instance, value):
        for (p, v) in zip(self.compound, value):
            p._validate(instance, v)
        for v in self.__class__._default_validators + self.validators:
            v(instance, value) if callable(v) else v.validate(instance, value)

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

    def _from_json_value(self, value):
        raise gripe.NotSerializableError(self.name)

    def _to_json_value(self, instance, value):
        raise gripe.NotSerializableError(self.name)


class StringProperty(ModelProperty):
    datatype = str
    sqltype = "TEXT"


TextProperty = StringProperty
StrProperty = StringProperty


class LinkProperty(StringProperty):
    _default_validators = []
    _default_validators.append(RegExpValidator("(|https?:\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)"))


class PasswordProperty(StringProperty):
    def __init__(self, *args, **kwargs):
        super(PasswordProperty, self).__init__(*args, **kwargs)
        self.private = True

    def _on_store(self, instance):
        value = self.__get__(instance, instance.__class__)
        self.__set__(instance, self.hash(value))

    @classmethod
    def hash(cls, password):
        return password \
            if password and password.startswith("sha://") \
            else "sha://%s" % hashlib.sha1(password if password else "").hexdigest()


class JSONProperty(ModelProperty):
    datatype = dict
    sqltype = "JSONB"

    def _initial_value(self):
        return {}


class ListProperty(ModelProperty):
    datatype = list
    sqltype = "JSONB"

    def _initial_value(self):
        return []


class IntegerProperty(ModelProperty):
    datatype = int
    sqltype = "INTEGER"


IntProperty = IntegerProperty


class FloatProperty(ModelProperty):
    datatype = float
    sqltype = "REAL"


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


class TimeDeltaProperty(ModelProperty):
    datatype = datetime.timedelta
    sqltype = "INTERVAL"


if gripe.db.Tx.database_type == "postgresql":
    import psycopg2.extensions

    def adapt_json(d):
        return psycopg2.extensions.AsIs("'%s'" % json.dumps(d))

    psycopg2.extensions.register_adapter(dict, adapt_json)
    psycopg2.extensions.register_adapter(list, adapt_json)

    def cast_jsonb(value, cur):
        try:
            return json.loads(value) if value is not None else None
        except:
            raise psycopg2.InterfaceError("bad JSON representation: %r" % value)

    with gripe.db.Tx.begin() as tx:
        cur = tx.get_cursor()
        cur.execute("SELECT NULL::jsonb")
        jsonb_oid = cur.description[0][1]

    JSONB = psycopg2.extensions.new_type((jsonb_oid,), "JSONB", cast_jsonb)
    psycopg2.extensions.register_type(JSONB)


elif gripe.db.Tx.database_type == "sqlite3":
    import sqlite3

    def adapt_json(d):
        return json.dumps(d)

    def convert_json(value):
        return json.loads(value) if value is not None else None

    sqlite3.register_adapter(dict, adapt_json)
    sqlite3.register_converter("JSONB", convert_json)
