# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Oct-2013 8:37:08 AM$"

from datetime import datetime
import json
import logging
import webapp2

import grumble
import grumble.geopt
import sweattrails.profile


from Athlete import Athlete
from Athlete import CriticalPowerDef
from Athlete import get_athlete_with_id
from Model.Config.SessionType import SessionType
import json_util
import Util

class Interval(grumble.Model):
    interval_id = db.IntegerProperty()
    part_of = db.SelfReferenceProperty()
    distance = db.IntegerProperty(default=0)         # Distance in meters
    duration = db.TimeProperty()
    average_hr = db.IntegerProperty(default=0)       # bpm
    max_hr = db.IntegerProperty(default=0)           # bpm
    work = db.IntegerProperty(default=0)	     # kJ
    num_intervals = db.IntegerProperty(default=0)
    num_waypoints = db.IntegerProperty(default=0)

    def get_session(self):
	ret = self.parent()
	while not isinstance(ret, Session):
	    ret = ret.parent()
	return ret

    def get_athlete(self):
	return self.get_session().parent()

    def toDict(self, deep = True):
	ret = {}
	athlete = self.get_athlete()
	ret['key'] = str(self.key())
	ret['type'] = self.type
	ret['seconds'] = Util.time_to_seconds(self.duration)
	ret['distance'] = float(Util.distance(self.distance, athlete.units, False))
	ret['average_hr'] = self.average_hr if self.average_hr else 0
	ret['max_hr'] = self.max_hr if self.max_hr else 0
	ret['work'] = self.work if self.work else 0
	ret['num_intervals'] = self.num_intervals if self.num_intervals else 0
	ret['interval_id'] = self.interval_id if self.interval_id else 0
        if deep:
            ret['intervals'] = Interval.toArray(self)
            for gd in self.geodata_set:
                ret['geodata'] = gd.toDict()
        if self.type == 'bike':
            self.includeBikeData(ret, athlete, deep)
        elif self.type == 'run':
            self.includeRunData(ret, athlete, deep)
	return ret

#class BikeData(IntervalData):
#    average_power = db.IntegerProperty(default=0)    # W
#    normalized_power = db.IntegerProperty()          # W
#    max_power = db.IntegerProperty(default=0)        # W
#    average_cadence = db.IntegerProperty(default=0)  # rpm
#    max_cadence = db.IntegerProperty(default=0)      # rpm
#    average_torque = db.FloatProperty(default=0.0)   # Nm
#    max_torque = db.FloatProperty(default=0.0)       # Nm
#    max_speed = db.FloatProperty(default=0.0)        # m/s

    def includeBikeData(self, dict, athlete, deep = True):
	dict['average_power'] = self.average_power if self.average_power else 0
	dict['normalized_power'] = self.normalized_power if self.normalized_power else 0
	dict['max_power'] = self.max_power if self.max_power else 0
	dict['average_cadence'] = self.average_cadence if self.average_cadence else 0
	dict['max_cadence'] = self.max_cadence if self.max_cadence else 0
	dict['average_torque'] = self.average_torque if self.average_torque else 0.0
	dict['max_torque'] = self.max_torque if self.max_torque else 0.0
	dict['average_speed'] = float(Util.avgspeed(self.distance, self.duration, athlete.units, False))
	dict['max_speed'] = float(Util.speed(self.max_speed, athlete.units, False))
        if deep:
            dict['critical_power'] = []
            for cp in CriticalPower.gql("WHERE interval = :1", self):
                dict['critical_power'].append(cp.toDict())
            dict['critical_power'].sort(key=lambda x: x['duration'])

#class RunData(IntervalData):
#    max_speed = db.FloatProperty(default=0.0)        # m/s

    def includeRunData(self, dict, athlete, deep = True):
	dict['average_speed'] = float(Util.avgspeed(self.distance, self.duration, athlete.units, False))
	dict['max_speed'] = float(Util.speed(self.max_speed, athlete.units, False))
	dict['average_pace'] = Util.avgpace(self.distance, self.duration, athlete.units, False)
	dict['best_pace'] = Util.pace(self.max_speed, athlete.units, False)


    @staticmethod
    def toArray(obj):
	ret = []
	if isinstance(obj, Session):
	    intervals = [ obj.interval ]
	else:
	    intervals = Interval.gql("WHERE part_of = :1 ORDER BY interval_id", obj)
	for interval in intervals:
	    ret.append(interval.toDict())
	return ret

    def rollback(self):
	subs = Interval.gql("WHERE ANCESTOR IS :1", self)
	for sub in subs:
	    sub.rollback()
	if self.num_waypoints > 0:
	    wps = Waypoint.gql("WHERE ANCESTOR IS :1", self)
	    for wp in wps:
		wp.delete()
	self.delete()

class CriticalPower(db.Model):
    interval = db.ReferenceProperty(Interval)
    cpdef = db.ReferenceProperty(CriticalPowerDef)
    start_time = db.TimeProperty()
    power = db.IntegerProperty()

    def toDict(self):
	best = None
	for b in self.cpdef.bestcriticalpower_set:
	    best = b
	if best:
	    best_pwr = best.best.power
	else:
	    best_pwr = 0
	return {
	    'power': self.power,
	    'label': self.cpdef.label,
	    'duration': self.cpdef.duration,
	    'timestamp': Util.time_to_seconds(self.start_time),
	    'best': best_pwr
	}

    def updateBestCriticalPower(self):
	best = None
	for bcp in BestCriticalPower.gql("WHERE ANCESTOR IS :1", self.interval.get_athlete()):
	    if bcp.cpdef.duration == self.cpdef.duration:
		best = bcp
	if not best:
	    best = BestCriticalPower(parent = self.cpdef)
	    best.cpdef = self.cpdef
	    best.best = None
	if best.best is None or self.power > best.best.power:
	    best.best = self
	best.put()

class BestCriticalPower(db.Model):
    cpdef = db.ReferenceProperty(CriticalPowerDef)
    best = db.ReferenceProperty(CriticalPower)

class GeoData(db.Model):
    interval = db.ReferenceProperty(Interval)
    max_elev = db.IntegerProperty(default=-100)      # In meters
    min_elev = db.IntegerProperty(default=10000)     # In meters
    elev_gain = db.IntegerProperty(default=0)        # In meters
    elev_loss = db.IntegerProperty(default=0)        # In meters
    max_loc_ne = db.GeoPtProperty()
    max_loc_sw = db.GeoPtProperty()

    def toDict(self):
	ret = {}
	ret['elev_gain'] = self.elev_gain if self.elev_gain else 0
	ret['elev_loss'] = self.elev_loss if self.elev_loss else 0
	ret['max_elev'] = self.max_elev if self.max_elev else -500
	ret['min_elev'] = self.min_elev if self.min_elev else 10000
	if self.max_loc_ne:
	    ret['max_ne'] = {
		'lat': self.max_loc_ne.lat,
		'lon': self.max_loc_ne.lon
	    }
	if self.max_loc_sw:
	    ret['max_sw'] = {
		'lat': self.max_loc_sw.lat,
		'lon': self.max_loc_sw.lon
	    }
	return ret

class Session(db.Model):
    athlete = db.UserProperty()
    interval = db.ReferenceProperty(Interval)
    description = db.StringProperty()
    session_start = db.DateTimeProperty()
    sessiontype = db.ReferenceProperty(SessionType)
    notes = db.StringProperty(multiline=True)
    posted = db.DateTimeProperty(auto_now_add=True)
    inprogress = db.BooleanProperty(default=True)
    device = db.StringProperty(default="")

    def get_athlete(self):
	return self.parent()

    def toDict(self, deep = True):
	ret = {}
	ret['key'] = str(self.key())
	ret['description'] = self.description if self.description else ''
	ret['notes'] = self.notes if self.notes else ''
	ret['start'] = json_util.datetime_to_dict(self.session_start)
	ret['sessiontype'] = self.sessiontype.name if self.sessiontype else ''
	ret['inprogress'] = self.inprogress
	ret['posted'] = json_util.datetime_to_dict(self.posted)
	ret['device'] = self.device if self.device else ''
	ret['interval'] = self.interval.toDict(deep)
	return ret

    def analyze(self):
	logging.info(" --- Analyze ---")

    def upload_slice(self, request):
	lines = request.get("slice").splitlines()
	for line in lines:
	    if (line.strip() != ''):
		wp = Waypoint(parent=self)
		wp.session = self
		(seqnr, lat, lon, speed, elapsed, timestamp, altitude, distance) = line.split(";")
		wp.seqnr = int(seqnr)
		wp.location = GeoPt(float(lat), float(lon))
		wp.speed = float(speed)
		wp.elapsed = seconds_to_time(elapsed)
		wp.timestamp = datetime.fromtimestamp(int(timestamp) // 1000)
		wp.altitude = float(altitude)
		wp.distance = float(distance)
		wp.put()

    def commit(self):
	self.inprogress = False
	self.put()

    @classmethod
    def create_session(cls, request, athlete):
        session = Session(parent=athlete)
        session.athlete = athlete.user
        session.description = request.get("description")
        session.distance = float(request.get("distance"))
        session.notes = request.get("notes")
        t = request.get("time", None)
        if t:
            secs = float(t)
        else:
            secs = int(request.get("seconds")) + int(request.get("minutes")) * 60 + int(request.get("hours")) * 3600
        session.session_time = Util.seconds_to_time(secs)
        typ = request.get("type", None)
        if typ:
            typ = 'run'
        session.sessiontype = typ
        session.put()
        if not athlete.uploads:
            athlete.uploads = 1
        else:
            athlete.uploads += 1
        athlete.last_upload = datetime.now()
        athlete.put()
        return session

class Waypoint(db.Model):
    interval = db.ReferenceProperty(Interval)
    seqnr = db.IntegerProperty()
    location = db.GeoPtProperty()
    speed = db.FloatProperty()		    # m/s
    timestamp = db.TimeProperty()
    elapsed = db.TimeProperty()
    altitude = db.IntegerProperty()	    # meters
    distance = db.IntegerProperty()	    # meters
    cadence = db.IntegerProperty()
    heartrate = db.IntegerProperty()
    power = db.IntegerProperty()
    torque = db.FloatProperty()
    
    def get_session(self):
	ret = self.parent()
	while not isinstance(ret, Session):
	    ret = ret.parent()
	return ret
    
    def get_athlete(self):
	return self.get_session().get_athlete()
  
    def toDict(self, athlete = None):
	if athlete is None:
	    athlete = self.get_athlete()
	return {
	    'key': str(self.key()),
	    'seqnr': self.seqnr,
	    'seconds': Util.time_to_seconds(self.timestamp),
	    'power': self.power if self.power else 0,
	    'speed': float(Util.speed(self.speed, athlete.units, False)) if self.speed else 0.0,
	    'torque': self.torque if self.torque else 0.0,
	    'heartrate': self.heartrate if self.heartrate else 0,
	    'cadence': self.cadence if self.cadence else 0,
	    'distance': float(Util.distance(self.distance, athlete.units, False)) if self.distance else 0.0,
	    'altitude': self.altitude if self.altitude else 0.0,
	    'location': {
		'lat': self.location.lat if self.location else 200, 
		'lon': self.location.lon if self.location else 200
	    }
        }
    
    @staticmethod
    def toArray(obj):
	if isinstance(obj, Session):
	    return Waypoint.toArray(obj.interval)
	ret = []
	wps = Waypoint.gql("WHERE ANCESTOR IS :1 ORDER BY seqnr", obj)
	athlete = obj.get_athlete()
	for wp in wps:
	    ret.append(wp.toDict(athlete))
	return ret

class SessionFile(db.Model):
    athlete = db.ReferenceProperty(reference_class=Athlete)
    next = db.SelfReferenceProperty()
    description = db.StringProperty()
    session_start = db.DateTimeProperty()
    filetype = db.StringProperty()
    blocks = db.IntegerProperty()
    data = db.TextProperty()

class JSON_Sessions(webapp2.RequestHandler):
    def get(self):
	user = users.get_current_user()
	ret = []
	if user:
	    athlete_id = self.request.get('athlete');
            athlete = get_athlete_with_id(athlete_id)
	    if athlete is not None:
                deep = self.request.get('deep')
                if deep and deep != '':
                    deep = (deep != 'false')
                else:
                    deep = False
		sessions = db.GqlQuery("SELECT * FROM Session WHERE ANCESTOR IS :1 ORDER BY session_start DESC LIMIT 25", athlete)
                for session in sessions:
                    ret.append(session.toDict(deep))
                retstr = json.dumps(ret)
                self.response.out.write(retstr)
            else:
                self.error(401)
        else:
            self.error(401)


class JSON_Session(webapp2.RequestHandler):
    def get(self):
	user = users.get_current_user()
	ret = {}
	if user:
	    athlete_id = self.request.get('athlete');
            athlete = get_athlete_with_id(athlete_id)
	    if athlete is not None:
		session = Session.get(self.request.get('id'))
		if session is not None:
		    ret = session.toDict()
        retstr = json.dumps(ret)
        self.response.out.write(retstr)

class JSON_SessionWaypoints(webapp2.RequestHandler):
    def get(self):
	user = users.get_current_user()
	ret = []
	if user:
	    athlete_id = self.request.get('athlete');
            athlete = get_athlete_with_id(athlete_id)
	    if athlete is not None:
		session = Session.get(self.request.get('id'))
		if session is not None:
		    ret = Waypoint.toArray(session)
        retstr = json.dumps(ret)
        self.response.out.write(retstr)

class JS_Session(webapp2.RequestHandler):
    def get(self):
	Util.js(self, "session", "sid")


