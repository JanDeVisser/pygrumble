# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$17-Sep-2013 12:23:49 PM$"

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
    def get(cls, datatype, property):
        return cls._converters[datatype](datatype, property) \
            if datatype in cls._converters \
            else PropertyConverter(datatype, property)

class PropertyConverter(object):
    __metaclass__ = Converters

    def __init__(self, datatype = None, property = None):
        self.property = property
        if datatype:
            self.datatype = datatype

    def convert(self, value):
        """
            Convert value from to the canonical internal representation. Raise
            an exception if value cannot be converted.
        """
        try:
            return self.datatype(value) if not isinstance(value, self.datatype) else value
        except:
            logger.exception("PropertyConverter<%s>.convert(%s [%s])", self.datatype, value, type(value))
            raise

    def to_sqlvalue(self, value):
        """
                Convert value, which is guaranteed to be produced by a call to
                convert(), to a value suitable for storing in persistant
                storage.
        """
        return value

    def from_sqlvalue(self, value):
        """
            Convert value, which was retrieved from persistant storage, to its
            canonical internal representation.
        """
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

    def to_jsonvalue(self, value):
        assert value is not None, "DictConverter.to_jsonvalue(): value should not be None"
        assert isinstance(value, dict), "DictConverter.to_jsonvalue(): value must be a dict"
        return dict(value)

    def from_jsonvalue(self, value):
        assert (value is None) or isinstance(value, dict), "DictConverter.from_jsonvalue(): value must be a dict"
        return value or {}

class ListConverter(PropertyConverter):
    datatype = list

    def convert(self, value):
        try:
            return list(value)
        except:
            return json.loads(str(value)) if value is not None else []

    def to_jsonvalue(self, value):
        assert value is not None, "ListConverter.to_jsonvalue(): value should not be None"
        assert isinstance(value, list), "ListConverter.to_jsonvalue(): value must be a list"
        return list(value)

    def from_jsonvalue(self, value):
        assert (value is None) or isinstance(value, list), "ListConverter.from_jsonvalue(): value must be a list"
        return value or []

class BooleanConverter(PropertyConverter):
    datatype = bool

    def convert(self, value):
        if isinstance(value, basestring) and self.property.choices and len(self.property.choices) == 2:
            value = self.property.choices.index(value) == 1
        return super(BooleanConverter, self).convert(value)

    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, bool), "BooleanConverter.to_jsonvalue: value must be bool"
        return self.property.choices[1 if value else 0] \
            if self.property.choices and len(self.property.choices) == 2 \
            else value

    def from_jsonvalue(self, value):
        if isinstance(value, basestring) and self.property.choices and len(self.property.choices) == 2:
            value = self.property.choices.index(value) == 1
        return super(BooleanConverter, self).from_jsonvalue(value)

class DateTimeConverter(PropertyConverter):
    datatype = datetime.datetime

    def convert(self, value):
        if isinstance(value, (int, float)):
            value = datetime.datetime.utcfromtimestamp(value)
        return super(DateTimeConverter, self).convert(value)

    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.datetime), "DateTimeConverter.to_jsonvalue: value must be datetime"
        return gripe.json_util.datetime_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_datetime(value) if isinstance(value, dict) else value

class DateConverter(PropertyConverter):
    datatype = datetime.date

    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.date), "DateConverter.to_jsonvalue: value must be date"
        return gripe.json_util.date_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_date(value) if isinstance(value, dict) else value

class TimeConverter(PropertyConverter):
    datatype = datetime.time

    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.time), "TimeConverter.to_jsonvalue: value must be time"
        return gripe.json_util.time_to_dict(value)

    def from_jsonvalue(self, value):
        return gripe.json_util.dict_to_time(value) if isinstance(value, dict) else value

class TimeDeltaConverter(PropertyConverter):
    datatype = datetime.timedelta

    def convert(self, value):
        if isinstance(value, (int, float)):
            value = datetime.timedelta(seconds = value)
        return super(TimeDeltaConverter, self).convert(value)

    def to_jsonvalue(self, value):
        assert (value is None) or isinstance(value, datetime.timedelta), "TimeDeltaConverter.to_jsonvalue: value must be timedelta"
        return value.total_seconds()

    def from_jsonvalue(self, value):
        return datetime.timedelta(seconds = value)

