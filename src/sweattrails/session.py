# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Oct-2013 8:37:08 AM$"

from datetime import datetime
import json

import gripe
import grizzle
import grumble
import grumble.geopt
import sweattrails.config
import sweattrails.userprofile

logger = gripe.get_logger(__name__)

@grumble.abstract
class IntervalPart(grumble.Model):
    def get_interval(self):
        pass

    def analyze(self):
        pass

class BikePart(IntervalPart):
    average_power = grumble.IntegerProperty(default = 0)  # W
    normalized_power = grumble.IntegerProperty()  # W
    max_power = grumble.IntegerProperty(default = 0)  # W
    average_cadence = grumble.IntegerProperty(default = 0)  # rpm
    max_cadence = grumble.IntegerProperty(default = 0)  # rpm
    average_torque = grumble.FloatProperty(default = 0.0)  # Nm
    max_torque = grumble.FloatProperty(default = 0.0)  # Nm
    max_speed = grumble.FloatProperty(default = 0.0)  # m/s
    vi = grumble.FloatProperty(default = 0.0)
    intensity_factor = grumble.FloatProperty(default = 0.0)
    tss = grumble.FloatProperty(default = 0.0)

    def analyze(self):
        pass

class RunPart(IntervalPart):
    average_cadence = grumble.IntegerProperty(default = 0)  # rpm
    max_cadence = grumble.IntegerProperty(default = 0)  # rpm
    max_speed = grumble.FloatProperty(default = 0.0)  # m/s

class SwimPart(IntervalPart):
    pass

class SessionTypeReference(grumble.reference.ReferenceProperty):
    def __init__(self, *args, **kwargs):
        kwargs["reference_class"] = sweattrails.config.SessionType
        super(SessionTypeReference, self).__init__(self, *args, **kwargs)

    def get_interval_part_type(self, sessiontype, interval):
        return sessiontype.get_interval_part_type(interval.get_activityprofile())

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
    interval_id = grumble.StringProperty(is_key = True)
    intervalpart = grumble.ReferenceProperty(IntervalPart)
    distance = grumble.IntegerProperty(default = 0)  # Distance in meters
    start_time = grumble.DateTimeProperty()
    elapsed_time = grumble.TimeProperty()  # Duration including pauses
    duration = grumble.TimeProperty()  # Time excluding pauses
    average_hr = grumble.IntegerProperty(default = 0)  # bpm
    max_hr = grumble.IntegerProperty(default = 0)  # bpm
    work = grumble.IntegerProperty(default = 0)  # kJ
    calories_burnt = grumble.IntegerProperty(default = 0)  # kJ

    def after_insert(self):
        sessiontype = self.get_sessiontype()
        if sessiontype:
            partcls = sessiontype.get_interval_part_type(self.get_activityprofile())
            part = partcls(parent = self)
            part.put()

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
        return sweattrails.config.ActivityProfile.get_profile(athlete)

    def on_delete(self):
        IntervalPart.query(parent = self).delete()
        Interval.query(parent = self).delete()

class CriticalPower(grumble.Model):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPowerInterval)
    start_time = grumble.TimeProperty()
    power = grumble.IntegerProperty()

    def after_store(self):
        best = None
        for bcp in BestCriticalPower.query(ancestor = self.interval.get_athlete()):
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
    max_elev = grumble.IntegerProperty(default = -100)  # In meters
    min_elev = grumble.IntegerProperty(default = 10000)  # In meters
    elev_gain = grumble.IntegerProperty(default = 0)  # In meters
    elev_loss = grumble.IntegerProperty(default = 0)  # In meters
    bounding_box = grumble.geopt.GeoBoxProperty()

class Session(Interval):
    athlete = grumble.ReferenceProperty(grizzle.User)
    description = grumble.StringProperty()
    sessiontype = SessionTypeReference()
    notes = grumble.StringProperty(multiline = True)
    posted = grumble.DateTimeProperty(auto_now_add = True)
    inprogress = grumble.BooleanProperty(default = True)
    device = grumble.StringProperty(default = "")

    def analyze(self):
        self.analyze()
        for i in Interval.query(parent = self):
            i.analyze()

    def upload_slice(self, request):
        lines = request.get("slice").splitlines()
        for line in lines:
            if (line.strip() == ''):
                continue
            wp = Waypoint(parent = self)
            wp.session = self
            (seqnr, lat, lon, speed, timestamp, altitude, distance) = line.split(";")
            wp.seqnr = int(seqnr)
            wp.location = GeoPt(float(lat), float(lon))
            wp.speed = float(speed)
            wp.timestamp = datetime.fromtimestamp(int(timestamp) // 1000)
            wp.altitude = float(altitude)
            wp.distance = float(distance)
            wp.put()

    def commit(self):
        self.inprogress = False
        self.put()

    def on_delete(self):
        Interval.query(parent = self).delete()
        Waypoint.query(ancestor = self).delete()

    @classmethod
    def create_session(cls, request, athlete):
        session = Session(parent = athlete)
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
    timestamp = grumble.TimeProperty(is_key = True)
    location = grumble.geopt.GeoPtProperty()
    speed = grumble.FloatProperty()  # m/s
    elapsed = grumble.TimeProperty()
    altitude = grumble.IntegerProperty()  # meters
    distance = grumble.IntegerProperty()  # meters
    cadence = grumble.IntegerProperty()
    heartrate = grumble.IntegerProperty()
    power = grumble.IntegerProperty()
    torque = grumble.FloatProperty()
    temperature = grumble.IntegerProperty()

    def get_session(self):
        return self.root()

    def get_athlete(self):
        return self.get_session().get_athlete()

class SessionFile(grumble.Model):
    athlete = grumble.ReferenceProperty(reference_class = grizzle.User)
    next = grumble.SelfReferenceProperty()
    description = grumble.StringProperty()
    session_start = grumble.DateTimeProperty()
    filetype = grumble.StringProperty()
    blocks = grumble.IntegerProperty()
    data = grumble.TextProperty()

