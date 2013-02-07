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
