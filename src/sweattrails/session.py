# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Oct-2013 8:37:08 AM$"

from datetime import datetime
import json
import webapp2

import gripe
import grizzle
import grumble
import grumble.geopt
import sweattrails.config
import sweattrails.userprofile

logger = gripe.get_logger(__name__)

@grumble.abstract
class IntervalPart(grumble.Model):
    def analyze(self):
        pass

class BikePart(IntervalPart):
    average_power = grumble.IntegerProperty(default=0)    # W
    normalized_power = grumble.IntegerProperty()          # W
    max_power = grumble.IntegerProperty(default=0)        # W
    average_cadence = grumble.IntegerProperty(default=0)  # rpm
    max_cadence = grumble.IntegerProperty(default=0)      # rpm
    average_torque = grumble.FloatProperty(default=0.0)   # Nm
    max_torque = grumble.FloatProperty(default=0.0)       # Nm
    max_speed = grumble.FloatProperty(default=0.0)        # m/s

class RunPart(IntervalPart):
    average_cadence = grumble.IntegerProperty(default=0)  # rpm
    max_cadence = grumble.IntegerProperty(default=0)      # rpm
    max_speed = grumble.FloatProperty(default=0.0)        # m/s

class SwimPart(IntervalPart):
    pass

class SessionTypeReference(grumble.reference.ReferenceProperty):
    _resolved_parts = set()

    def get_interval_part_type(self, sessiontype, interval):
        profile = interval.get_activityprofile()
        node = profile.get_node(sweattrails.config.SessionType, sessiontype.name)
        part = node.get_root_property("intervalpart")
        if part not in self._resolved_parts:
            logger.debug("sweattrails.session.SessionTypeReference.get_interval_part_type(%s): Resolving part %s", sessiontype.name, part)
            gripe.resolve(part)
            self._resolved_parts.add(part)
        return grumble.Model.for_name(part)
    
    def after_set(self, session, old_sessiontype, new_sessiontype):
        if not old_sessiontype or (old_sessiontype.name != new_sessiontype.name):
            if session.intervalpart:
                grumble.delete(session.intervalpart)
            t = self.get_interval_part_type(new_sessiontype, session)
            session.intervalpart = t(parent = session)
            session.intervalpart.put()
            for i in Interval.query(ancestor = session):
                if i.intervalpart:
                    grumble.delete(i.intervalpart)
                i.intervalpart = t(parent = i)
                i.intervalpart.put()
        

class Interval(grumble.Model):
    interval_id = grumble.IntegerProperty()
    intervalpart = grumble.ReferenceProperty(IntervalPart)
    distance = grumble.IntegerProperty(default=0)         # Distance in meters
    duration = grumble.TimeProperty()
    average_hr = grumble.IntegerProperty(default=0)       # bpm
    max_hr = grumble.IntegerProperty(default=0)           # bpm
    work = grumble.IntegerProperty(default=0)             # kJ
    num_intervals = grumble.IntegerProperty(default=0)
    num_waypoints = grumble.IntegerProperty(default=0)
    
    def analyze(self):
        self.intervalpart.analyze()
        for i in Interval.query(parent = self):
            i.analyze()

    def get_session(self):
	return self.root()
    
    def get_sessiontype(self):
        return self.get_session().sessiontype    
    
    def get_athlete(self):
	return self.get_session().athlete
    
    def get_activityprofile(self):
        athlete = self.get_athlete()
        return athlete.activityprofile

    def get_interval_part_type(self):
        sessiontype = self.get_sessiontype()
        profile = self.get_activityprofile()
        node = profile.get_node(sweattrails.config.SessionType, sessiontype.name)
        part = node.get_root_property("intervalpart")
        if part not in self._resolved_parts:
            logger.debug("sweattrails.session.Interval.get_interval_part(%s): Resolving part %s", sessiontype.name, part)
            gripe.resolve(part)
            self._resolved_parts.add(part)
        return grumble.Model.for_name(part)
    
    
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    def rollback(self):
        for wp in Waypoint.gql(ancestor = self):
            grumble.delete(wp)
	if self.num_waypoints > 0:
	    wps = Waypoint.gql("WHERE ANCESTOR IS :1", self)
	    for wp in wps:
		wp.delete()
	self.delete()

class CriticalPower(grumble.Model):
    interval = grumble.ReferenceProperty(Interval)
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPowerInterval)
    start_time = grumble.TimeProperty()
    power = grumble.IntegerProperty()

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

class BestCriticalPower(grumble.Model):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPowerInterval)
    best = grumble.ReferenceProperty(CriticalPower)

class GeoData(grumble.Model):
    interval = grumble.ReferenceProperty(Interval)
    max_elev = grumble.IntegerProperty(default=-100)      # In meters
    min_elev = grumble.IntegerProperty(default=10000)     # In meters
    elev_gain = grumble.IntegerProperty(default=0)        # In meters
    elev_loss = grumble.IntegerProperty(default=0)        # In meters
    max_loc_ne = grumble.GeoPtProperty()
    max_loc_sw = grumble.GeoPtProperty()

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

class Session(Interval):
    athlete = grumble.ReferenceProperty(grizzle.User)
    description = grumble.StringProperty()
    session_start = grumble.DateTimeProperty()
    sessiontype = grumble.ReferenceProperty(sweattrails.config.SessionType)
    notes = grumble.StringProperty(multiline=True)
    posted = grumble.DateTimeProperty(auto_now_add=True)
    inprogress = grumble.BooleanProperty(default=True)
    device = grumble.StringProperty(default="")

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

class Waypoint(grumble.Model):
    interval = grumble.ReferenceProperty(Interval)
    seqnr = grumble.IntegerProperty()
    location = grumble.GeoPtProperty()
    speed = grumble.FloatProperty()		    # m/s
    timestamp = grumble.TimeProperty()
    elapsed = grumble.TimeProperty()
    altitude = grumble.IntegerProperty()	    # meters
    distance = grumble.IntegerProperty()	    # meters
    cadence = grumble.IntegerProperty()
    heartrate = grumble.IntegerProperty()
    power = grumble.IntegerProperty()
    torque = grumble.FloatProperty()
    
    def get_session(self):
	ret = self.root()
    
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

class SessionFile(grumble.Model):
    athlete = grumble.ReferenceProperty(reference_class=Athlete)
    next = grumble.SelfReferenceProperty()
    description = grumble.StringProperty()
    session_start = grumble.DateTimeProperty()
    filetype = grumble.StringProperty()
    blocks = grumble.IntegerProperty()
    data = grumble.TextProperty()

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
		sessions = grumble.GqlQuery("SELECT * FROM Session WHERE ANCESTOR IS :1 ORDER BY session_start DESC LIMIT 25", athlete)
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


