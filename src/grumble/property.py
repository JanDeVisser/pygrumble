# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 1:24:18 PM$"

import datetime
import hashlib

import gripe
import grumble.converter
import grumble.errors
import grumble.model
import grumble.schema

logger = gripe.get_logger(__name__)

class ModelProperty(object):
    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], ModelProperty):
            prop = args[0]
            ret = super(ModelProperty, prop.__class__).__new__(prop.__class__)
            ret.name = prop.name
            ret.column_name = prop.column_name
            ret.verbose_name = prop.verbose_name
            ret.required = prop.required
            ret.default = prop.default
            ret.private = prop.private
            ret.transient = prop.transient
            ret.is_label = prop.is_label
            ret.is_key = prop.is_key
            ret.scoped = prop.scoped
            ret.indexed = prop.indexed
            ret.validator = prop.validator
            ret.regexp = prop.regexp
            ret.suffix = prop.suffix
            ret.choices = prop.choices
            ret.converter = prop.converter
            ret.inherited_from = prop
        else:
            ret = super(ModelProperty, cls).__new__(cls)
            ret.name = args[0] if args else None
            ret.column_name = kwargs.get("column_name", cls.column_name if hasattr(cls, "column_name") else None)
            ret.verbose_name = kwargs.get("verbose_name", cls.verbose_name if hasattr(cls, "verbose_name") else ret.name)
            ret.required = kwargs.get("required", cls.required if hasattr(cls, "required") else False)
            ret.default = kwargs.get("default", cls.default if hasattr(cls, "default") else None)
            ret.private = kwargs.get("private", cls.private if hasattr(cls, "private") else False)
            ret.transient = kwargs.get("transient", cls.transient if hasattr(cls, "transient") else False)
            ret.is_label = kwargs.get("is_label", cls.is_label if hasattr(cls, "is_label") else False)
            ret.is_key = kwargs.get("is_key", cls.is_key if hasattr(cls, "is_key") else False)
            ret.scoped = kwargs.get("scoped", cls.scoped if hasattr(cls, "scoped") else False) if ret.is_key else False
            ret.indexed = kwargs.get("indexed", cls.indexed if hasattr(cls, "indexed") else False)
            ret.regexp = kwargs.get("regexp", cls.regexp if hasattr(cls, "regexp") else None)
            ret.suffix = kwargs.get("suffix", cls.suffix if hasattr(cls, "suffix") else None)
            ret.choices = kwargs.get("choices", cls.choices if hasattr(cls, "choices") else None)
            ret.converter = kwargs.get("converter", \
                cls.converter \
                    if hasattr(cls, "converter") \
                    else grumble.converter.Converters.get(cls.datatype)
            )
            ret.inherited_from = None
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
        ret = grumble.schema.ColumnDefinition(self.column_name, self.sqltype, self.required, self.default, self.indexed)
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

    def _after_store(self, value):
        pass

    def _validate(self, value):
        if (value is None) and self.required:
            raise grumble.errors.PropertyRequired(self.name)
        if self.choices and value not in self.choices and value:
            raise grumble.errors.InvalidChoice(self.name, value)
        if self.regexp and value and not re.match(self.regexp, value):
            raise grumble.errors.PatternNotMatched(self.name, value)
        self.validator(value)
        
    def validator(self, value):
        if hasattr(self, "validate") and callable(self.validate):
            self.validate(instance, value)

    def _update_fromsql(self, instance, values):
        instance._values[self.name] = self._from_sqlvalue(values[self.column_name])

    def _values_tosql(self, instance, values):
        if not self.transient:
            values[self.column_name] = self._to_sqlvalue(self.__get__(instance))

    def __get__(self, instance, owner = None):
        try:
            if not instance:
                return self
            if self.transient and hasattr(self, "getvalue") and callable(self.getvalue):
                return self.getvalue(instance)
            else:
                instance._load()
                return instance._values[self.name] if self.name in instance._values else None
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
                instance._values[self.name] = self.convert(value) if value is not None else None
                new = instance._values[self.name] if self.name in instance._values else None
                if hasattr(self, "after_set") and callable(self.after_set):
                    self.after_set(instance, old, new)
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

    def _after_store(self, value):
        for p in self.compound:
            p._after_store(value)

    def _validate(self, value):
        for (p, v) in zip(self.compound, value):
            p._validate(v)
        if hasattr(self, "validate") and callable(self.validate):
            self.validate(instance, value)

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

class TextProperty(StringProperty):
    pass

class LinkProperty(StringProperty):
    regexp = "(|https?:\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)"

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


