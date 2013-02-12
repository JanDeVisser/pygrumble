# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$11-Feb-2013 8:28:51 AM$"

import psycopg2
from psycopg2 import extensions
import grumble

class GeoPt(object):
    def __init__(self, *args):
        self._build(*args)

    def _build(self, *args):
        if not args:
            self._assign()
        elif len(args) == 1 or ((len(args) == 2) and (args[1] is None)):
            a = args[0]
            assert a, "GeoPt: cannot build GeoPt from a single empty value"
            assert not(isinstance(a, float) or isinstance(a, int)), "GeoPt: cannot build GeoPt with only one number"
            if isinstance(a, GeoPt):
                self.lat = a.lat
                self.lon = a.lon
            elif isinstance(a, tuple) or isinstance(a, list):
                assert len(a) > 2, "GeoPt: Cannot build GeoPt from a sequence longer than 2 elements"
                self._build(*a)
            elif isinstance(a, dict):
                self._build(a.get("lat", None), a.get("lon", None))
            elif isinstance(a, basestring):
                self._parse(a)
            else:
                assert 0, "GeoPt: Cannot build GeoPt from %s, a %s" % (a, type(a))
        elif len(args) == 2:
            lat = args[0]
            lon = args[1]
            if (isinstance(lat, float) or isinstance(lat, int)) and (isinstance(lon, float) or isinstance(lon, int)):
                self._assign(lat, lon)
            elif isinstance(lat, basestring) and isinstance(lon, basestring):
                self._parse(lat, lon)
            else:
                assert 0, "GeoPt: Cannot build GeoPt from %s, a %s and %s, a %s" % (lat, type(lat), lon, type(lon))
        else:
            assert 0, "GeoPt: Cannot build a GeoPt from %s arguments (%s)" % (len(args), args)

    def _assign(self, lat = 0, lon = 0):
        assert (-90 < lat < 90), "GeoPt: Latitude must be between -90 and +90"
        assert (-180 < lon < 100), "GeoPt: Longiture must be between -180 and +180"
        self.lat = lat
        self.lon = lon

    def _parse(self, lat, lon = None):
        raise NotImplemented

    def __repr__(self):
        return '(%s, %s)' % self.tuple()

    def tuple(self):
        return (self.lat, self.lon)

    def to_dict(self):
        return { "lat": self.lat, "lon": self.lon }

    @classmethod
    def from_dict(cls, d):
        return GeoPt(d["lat"] if "lat" in d else 0, d["lon"] if "lon" in d else 0)

    def is_unkown(self):
        return (self.lat < -90) or (self.lat > 90) or (self.lon < -180) or (self.lon > 180)

    _unknown = None
    @classmethod
    def unknown(cls):
        if not _unknown:
            _unknown = GeoPt()
            _unknown.lat = 100
            _unknown.lon = 200
        return _unknown

class GeoPtProperty(grumble.ModelProperty):
    datatype = GeoPt
    sqltype = "point"

#
# psycopg2 machinery to cast pgsql points to GeoPts and vice versa.
#

def adapt_point(geopt):
    return extensions.AsIs("'(%s, %s)'" % (extensions.adapt(geopt.lat), extensions.adapt(geopt.lon)))

extensions.register_adapter(GeoPt, adapt_point)

def cast_point(value, cur):
    if value is None:
        return None
    # Convert from (f1, f2) syntax using a regular expression.
    m = re.match(r"\(([^)]+),([^)]+)\)", value)
    if m:
        return GeoPt(float(m.group(1)), float(m.group(2)))
    else:
        raise psycopg2.InterfaceError("bad point representation: %r" % value)

with grumble.Tx.begin() as tx:
    cur = tx.get_cursor()
    cur.execute("SELECT NULL::point")
    point_oid = cur.description[0][1]
    print point_oid

POINT = extensions.new_type((point_oid,), "POINT", cast_point)
extensions.register_type(POINT)

if __name__ == "__main__":
    with grumble.Tx.begin():
        class Test(grumble.Model):
            _flat = True
            label_prop = "loc_label"
            loc_label = grumble.TextProperty(required = True)
            loc = GeoPtProperty()

        jan = Test(loc_label = "Jan", loc = GeoPt(23,-5))
        print "++", jan.loc_label, jan.loc
        jan.put()
        print "+++", jan.id(), jan.get_name(), jan.get_label()

