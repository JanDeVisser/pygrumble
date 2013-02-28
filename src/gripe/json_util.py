import datetime

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

    @classmethod
    def load(cls, obj):
        if isinstance(obj, basestring):
            obj = json.loads(obj)
        assert isinstance(obj, dict), "JSON.load: obj must be dict, not %s" % type(obj)
        return JSONObject(obj)

class JSONArray(list, JSON):
    def __init__(self, l):
        assert isinstance(l, list)
        self._data = l
        for obj in l:
            self.append(obj)

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
    def __init__(self, d):
        assert isinstance(d, dict)
        self._data = d
        for name in d:
            self[name] = d[name]

    def __getattr__(self, key):
        return None

    def __setitem__(self, key, value):
        o = self._convert(value)
        super(JSONObject, self).__setitem__(key, o)
        setattr(self, key, o)

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
