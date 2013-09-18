# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 12:23:49 PM$"

import datetime
import json

import gripe

logger = gripe.get_logger(__name__)

class Converters(type):
    _converters = { }
    
    def __new__(cls, name, bases, dct):
        ret = type.__new__(cls, name, bases, dct)
        if hasattr(ret, "datatypes"):
            for datatype in ret.datatypes:
                Converters._converters[datatype] = ret
        elif hasattr(ret, "datatype"):
            Converters._converters[ret.datatype] = ret
        return ret

    @classmethod
    def get(cls, datatype):
        return cls._converters[datatype]() \
            if datatype in cls._converters \
            else PropertyConverter(datatype)

class PropertyConverter(object):
    __metaclass__ = Converters

    def __init__(self, datatype = None):
        if datatype:
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
    datatype = dict

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
    datatype = list
        
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
    datatype = datetime.datetime
        
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.datetime), "DateTimeConverter.to_jsonvalue: value must be datetime"
        return gripe.json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_datetime(value) if isinstance(value, dict) else value
    
class DateConverter(PropertyConverter):
    datatype = datetime.date
    
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.date), "DateConverter.to_jsonvalue: value must be date"
        return gripe.json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_datetime(value) if isinstance(value, dict) else value

class TimeConverter(PropertyConverter):
    datatype = datetime.time
    
    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.time), "TimeConverter.to_jsonvalue: value must be time"
        return gripe.json_util.time_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_time(value) if isinstance(value, dict) else value

    