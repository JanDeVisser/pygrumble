#import sys
#import os.path
#if "C:\\Users\\jan\\Documents\Projects\\Grumble\\src" not in sys.path:
#    sys.path.insert(0, "C:\\Users\\jan\\Documents\Projects\\Grumble\\src")
#print sys.path

import datetime
import json

import gripe

def date_to_dict(d):
    if not(d):
        return None
    elif isinstance(d, datetime.date) or isinstance(d, datetime.datetime):
	return {
	    'year': d.year,
	    'month': d.month,
	    'day': d.day
	}
    else:
	return {
	    'year': 0,
	    'month': 0,
	    'day': 0
	}

def dict_to_date(d):
    return datetime.date(d['year'], d['month'], d['day']) \
        if (d and (d['year'] > 0) and (d['month'] > 0)) else None

def datetime_to_dict(ts):
    if not(ts):
        return None
    elif isinstance(ts, datetime.datetime):
	return {
	    'year': ts.year,
	    'month': ts.month,
	    'day': ts.day,
	    'hour': ts.hour,
	    'minute': ts.minute,
	    'second': ts.second
	}
    else:
	return {
	    'year': 0,
	    'month': 0,
	    'day': 0,
	    'hour': 0,
	    'minute': 0,
	    'second': 0
	}

def dict_to_datetime(d):
    return datetime.datetime(d['year'], d['month'], d['day'], d['hour'], d['minute'], d['second']) \
        if (d and (d['year'] > 0) and (d['month'] > 0)) else None

def time_to_dict(t):
    if not(t):
        return None
    elif isinstance(t, datetime.time) or isinstance(t, datetime.datetime):
        return {
            'hour': t.hour,
            'minute': t.minute,
            'second': t.second
        }
    else:
	return {
	    'hour': 0,
	    'minute': 0,
	    'second': 0
	}

def dict_to_time(d):
    return datetime.time(d['hour'], d['minute'], d['second']) if d else None

class JSON(object):
    def _convert(self, obj):
        if isinstance(obj, dict):
            keys = set(obj.keys())
            if keys == set(["hour", "minute", "second"]):
                return dict_to_time(obj)
            elif keys == set(["day", "month", "year"]):
                return dict_to_date(obj)
            elif keys == set(["day", "month", "year", "hour", "minute", "second"]):
                return dict_to_datetime(obj)
            else:
                return JSONObject(obj)
        elif isinstance(obj, list):
            return JSONArray(obj)
        else:
            return obj

    def _convert_out(self, obj):
        if isinstance(obj, datetime.datetime):
            return datetime_to_dict(obj)
        elif isinstance(obj, datetime.date):
            return date_to_dict(obj)
        elif isinstance(obj, datetime.time):
            return time_to_dict(obj)
        elif isinstance(obj, dict):
            return { k: self._convert_out(v) for (k,v) in obj.items() }
        elif isinstance(obj, list):
            return [self._convert_out(v) for v in obj]
        else:
            return obj

    @classmethod
    def load(cls, obj):
        if isinstance(obj, basestring):
            obj = json.loads(obj)
        assert isinstance(obj, dict), "JSON.load: obj must be dict, not %s" % type(obj)
        return JSONObject(obj)

    @classmethod
    def db_get(cls, db, key):
        data = db.get(str(key))
        ret = cls.load(data) if data else None
        if ret:
            ret._db = db
            ret._id = key
        return ret

    @classmethod
    def file_read(cls, fname):
        data = gripe.read_file(fname)
        return cls.load(data) if data else None
        
class JSONArray(list, JSON):
    def __init__(self, l):
        assert isinstance(l, list)
        self.extend(l)

    def append(self, value):
        o = self._convert(value)
        super(JSONArray, self).append(o)        

    def extend(self, l):
        for i in l:
            self.append(i)
            
    def __setitem__(self, key, value):
        o = self._convert(value)
        super(JSONArray, self).__setitem__(key, o)

class JSONObject(dict, JSON):
    def __init__(self, d = None):
        self._id = None
        self._db = None
        assert not d or isinstance(d, dict)
        if d:
            for (k, v) in d.items():
                if k not in ("_id", "_db"):
                    self[k] = v

    def __getattr__(self, key):
        return self[key] if key in self else None
        
    def __setattr__(self, key, value):
        if key in ("_db", "_id"):
            super(JSONObject, self).__setattr__(key, value)
        else:
            self[key] = value
        
    def __delattr__(self, key):
        del self[key]

    def __setitem__(self, key, value):
        o = self._convert(value)
        super(JSONObject, self).__setitem__(key, o)
        
    def merge(self, other):
        assert isinstance(other, JSONObject), "Can only merge JSONObjects"
        for (k, v) in other.items():
            myval = self.get(k)
            if k not in self:
                self[k] = v
                continue
            elif isinstance(v, list) and v:
                assert isinstance(myval, list), "Can only merge two lists when merging JSONObjects"
                if v[-1] == "+":
                    for x in v[0:-1]:
                        myval.insert(0, x)
                else:
                    myval.extend(v)
                continue
            elif isinstance(v, dict) and v:
                assert isinstance(myval, dict), "Can only merge two dicts when merging JSONObjects"
                if isinstance(myval, JSONObject) and isinstance(v, JSONObject):
                    myval.merge(v)
                else:
                    myval.update(v)
                continue
            else:
                # Overwrite current value with value from other:
                self[k] = v
        
    def json_str(self):
        return json.dumps(self._convert_out(self))
        
    def db_put(self, db = None, id = None):
        self._db = db if db is not None else self._db
        self._id = id if id is not None else self._id
        assert self._db is not None
        assert self._id is not None
        self._db[str(self._id)] = self.json_str()
        
    def file_write(self, fname):
        gripe.write_file(fname, self.json_str(), "w")
        
    def id(self):
        return self._id

if __name__ == "__main__":
    import json

    s = """{
"foo": [ 1, 2, 3.0, null, { "hex": "hop", "flux": 32 }, false ],
"bar": {
"quux": 12, "froz": "grob"
},
"nopope_date": { "day": 28, "month": 2, "year": 2013 },
"nopope": { "day": 28, "month": 2, "year": 2013, "hour": 18, "minute": 0, "second": 0 },
"nopope_time": { "hour": 18, "minute": 0, "second": 0 }
}"""
    obj = json.loads(s)
 
    o = JSON.load(s)
    print o
    print o.foo
    print o.foo[1]
    print o.foo[4].hex
    print o.bar.quux
    print o.bar.froz

    o = JSON.load(obj)
    print o
    print o.foo
    print o.foo[1]
    print o.foo[4].hex
    print o.bar.quux
    print o.bar.froz
    print o.nopope, type(o.nopope)
    print o.nopope_date, type(o.nopope_date)
    print o.nopope_time, type(o.nopope_time)

    print o.fake
    
    o = JSONObject()
    o.foo = 42
    o.foo_dict = {'a': 1, 'b': 2}
    o.foo_list = [1,2]
    print o
    
    p = JSONObject()
    p.foo = 43
    p.foo_dict = {'a': 3, 'b': 4}
    p.foo_list = [3,4]
    print p
    
    o.merge(p)
    print o
    
    
