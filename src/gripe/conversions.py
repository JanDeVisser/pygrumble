'''
Created on Aug 12, 2014

@author: jan
'''

import datetime
import math
import time

def local_date_to_utc(d):
    """Local date to UTC"""
    return datetime.datetime.utcfromtimestamp(time.mktime(d.timetuple()))

def semicircle_to_degrees(semicircles):
    """Convert a number in semicircles to degrees"""
    return semicircles * (180.0 / 2.0 ** 31)

def ms_to_kmh(ms):
    """Convert a speed in m/s (meters per second) to km/h (kilometers per hour)"""
    return (ms if ms else 0) * 3.6

def ms_to_mph(ms):
    """Convert a speed in m/s (meters per second) to mph (miles per hour)"""
    return (ms if ms else 0) * 2.23693632

def ms_to_minkm(ms):
    """Convert a speed in m/s (meters per second) to a pace in minutes per km"""
    return _pace(ms_to_kmh(ms))

def ms_to_minmile(ms):
    """Convert a speed in m/s (meters per second) to a pace in minutes per mile"""
    return _pace(ms_to_mph(ms))

def _pace(speed):
    if speed > 0:
        p = 60 / speed
        pmin = math.floor(p)
        psec = math.floor((p - pmin) * 60)
        return "%d'%02d\"" % (pmin, psec)
    else:
        return ""

def km_to_mile(km):
    """Convert a distance in km (kilometers) to miles"""
    return km * 0.621371192
