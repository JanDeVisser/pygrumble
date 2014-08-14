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
import grumble.property
import grumble.reference
import sweattrails.config
import sweattrails.userprofile

logger = gripe.get_logger(__name__)


class Reducer(object):
    def init_reducer(self):
        pass

    def reduce(self, value):
        return self

    def reduction(self):
        pass

class Reducers(list):
    def reduce(self, iterable):
        def run(reducers, item):
            for r in reducers:
                r.reduce(item)
            return reducers
        for r in self:
            r.init_reducer()
        reduce(run, iterable, self)
        for r in self:
            r.reduction()

class SimpleReducer(Reducer):
    def __init__(self, item_prop, target, aggr_prop):
        self.item_prop = item_prop
        self.aggr_prop = aggr_prop
        self.target = target
        self.cur = None
        self.count = 0

    def reduce(self, item):
        value = getattr(item, self.item_prop)
        self.cur = self.reducevalue(value)
        self.count += 1
        return self

    def reduction(self):
        finalvalue = self.finalize()
        setattr(self.target, self.aggr_prop, finalvalue)

    def finalize(self):
        return self.cur


class Accumulate(SimpleReducer):
    def reducevalue(self, value):
        return (self.cur if self.cur is not None else 0) + value


class AverageOverSamples(Accumulate):
    def finalize(self):
        return int(round(self.cur / self.count)) if self.count > 0 else 0

class AverageOverTime(SimpleReducer):
    def __init__(self, item_timestamp, item_prop, target, aggr_prop):
        super(AverageOverTime, self).__init__(item_prop, target, aggr_prop)
        self.item_timestamp = item_timestamp
        self.starttime = None
        self.lasttime = None
        self.maxvalue = None
        self.minvalue = None

    def reduce(self, item):
        ts = getattr(item, self.item_timestamp)
        value = getattr(item, self.item_prop)
        value = value if value is not None else 0
        if self.starttime is None:
            self.starttime = self.lasttime = ts
        diff = (ts - self.lasttime).seconds
        diff = diff if diff > 0 else 1
        if self.cur is None:
            self.cur = 0
        self.cur += diff * value
        self.maxvalue = max(self.minvalue, value)
        self.minvalue = min(self.minvalue, value)
        self.count += 1
        self.lasttime = ts
        return self

    def finalize(self):
        diff = (self.lasttime - self.starttime).seconds
        return int(round(self.cur) / diff) if diff > 0 else 0


class MaximizeAndAverageOverTime(AverageOverTime):
    def __init__(self, item_timestamp, item_prop, target, max_prop, avg_prop):
        super(MaximizeAndAverageOverTime, self).__init__(item_timestamp, item_prop, target, avg_prop)
        self.max_prop = max_prop

    def reduction(self):
        super(MaximizeAndAverageOverTime, self).reduction()
        setattr(self.target, self.max_prop, self.maxvalue)


class Maximize(SimpleReducer):
    def reducevalue(self, value):
        return max(self.cur, value)


class Minimize(SimpleReducer):
    def reducevalue(self, value):
        return min(self.cur, value)


class UpdatePolicy():
    DONT_UPDATE, UPDATE_WITH_OFFSET, UPDATE_ABSOLUTE = range(3)

    def __init__(self, distance, duration):
        self.distance = distance
        self.duration = duration

@grumble.abstract
class IntervalPart(grumble.Model):
    def _get_date(self):
        return self.get_session().start_time

    def get_interval(self):
        return self.parent()()

    def get_session(self):
        return self.root()

    def get_athlete(self):
        return self.get_session().athlete

    def get_activityprofile(self):
        return self.get_interval().get_activityprofile()

    def reducers(self):
        return []

    def analyze(self):
        pass


class CriticalPower(grumble.Model, Reducer):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPowerInterval)
    timestamp = grumble.TimeDeltaProperty()
    power = grumble.IntegerProperty()

    def init_reducer(self):
        self.rollingwindow = []
        self.starttime = None
        self.max_avg = None

    def reduce(self, wp):
        self.rollingwindow.append((wp.timestamp, wp.power))
        while (wp.timestamp - self.rollingwindow[0][0]) > self.cpdef.duration:
            del self.rollingwindow[0]
        diff = (wp.timestamp - self.rollingwindow[0][0]).seconds
        if diff >= (self.cpdef.duration.seconds) - 1:
            prev = None
            s = 0
            starttime = self.rollingwindow[0][0]
            for p in self.rollingwindow:
                td = (p[0] - prev[0]).seconds if prev else 1
                prev = p
                s += p[1] * td
            if prev:
                diff = (prev[0] - starttime).seconds
                if diff:
                    avg = int(round(s / diff))
                    if self.max_avg is None or avg > self.max_avg:
                        self.max_avg = avg
                    self.starttime = starttime
        return self

    def reduction(self):
        if self.starttime is not None:
            self.power = self.max_avg
            self.timestamp = self.starttime
            self.put()

    def after_store(self):
        best = None
        q = BestCriticalPower.query(parent = self.cpdef).add_sort("snapshotdate")
        q.add_filter("snapshotdate <= ", self.parent()().get_session().start_time)
        best = q.get()
        if not best or self.power > best.power:
            best = BestCriticalPower(parent = self.cpdef)
            best.best = self
            best.power = self.power
            best.put()


class BestCriticalPower(grumble.Model):
    snapshotdate = grumble.DateTimeProperty(auto_now_add = True)
    best = grumble.ReferenceProperty(CriticalPower)
    power = grumble.IntegerProperty(default = 0)


class WattsPerKgProperty(grumble.FloatProperty):
    transient = True
    def __init__(self, **kwargs):
        super(WattsPerKgProperty, self).__init__(**kwargs)
        self.power_prop = kwargs["powerproperty"]

    def getvalue(self, instance):
        session = instance.get_session()
        user = session.athlete
        ret = 0
        weightpart = user.get_part(sweattrails.userprofile.WeightMgmt)
        if weightpart is not None:
            weight = weightpart.get_weight(session.start_time)
            if weight > 0:
                power = getattr(instance, self.power_prop)
                if power is not None and power > 0:
                    ret = power / weight
        return ret

    def setvalue(self, instance, value):
        pass


class BikePart(IntervalPart):
    average_power = grumble.IntegerProperty(default = 0)  # W
    average_watts_per_kg = WattsPerKgProperty(powerproperty = "average_power")
    normalized_power = grumble.IntegerProperty()  # W
    normalized_watts_per_kg = WattsPerKgProperty(powerproperty = "normalized_power")
    max_power = grumble.IntegerProperty(default = 0)  # W
    max_watts_per_kg = WattsPerKgProperty(powerproperty = "max_power")
    average_cadence = grumble.IntegerProperty(default = 0)  # rpm
    max_cadence = grumble.IntegerProperty(default = 0)  # rpm
    average_torque = grumble.FloatProperty(default = 0.0)  # Nm
    max_torque = grumble.FloatProperty(default = 0.0)  # Nm
    vi = grumble.FloatProperty(default = 0.0)
    intensity_factor = grumble.FloatProperty(default = 0.0)
    tss = grumble.FloatProperty(default = 0.0)

    def get_ftp(self):
        interval = self.parent()()
        athlete = interval.get_athlete()
        bikepart = sweattrails.userprofile.BikeProfile.get_userpart(athlete)
        return bikepart.get_ftp(self.get_date()) if bikepart is not None else 0

    def get_max_power(self):
        interval = self.parent()()
        athlete = interval.get_athlete()
        bikepart = sweattrails.userprofile.BikeProfile.get_userpart(athlete)
        return bikepart.get_max_power(self.get_date()) if bikepart is not None else 0

    def set_max_power(self, max_power):
        interval = self.parent()()
        athlete = interval.get_athlete()
        bikepart = sweattrails.userprofile.BikeProfile.get_userpart(athlete)
        if bikepart is not None:
            bikepart.set_max_power(max_power, self.get_date())

    def get_watts_per_kg(self, watts):
        interval = self.parent()()
        athlete = interval.get_athlete()
        bikepart = sweattrails.userprofile.BikeProfile.get_userpart(athlete)
        return bikepart.get_watts_per_kg(watts, self.get_date()) if bikepart is not None else 0

    def reducers(self):
        ret = []
        for cpdef in self.get_activityprofile().get_all_linked_references(sweattrails.config.CriticalPowerInterval):
            if cpdef.duration <= self.get_interval().duration:
                cp = CriticalPower(parent = self)
                cp.cpdef = cpdef
                cp.put()
                ret.append(cp)
        ret.extend((MaximizeAndAverageOverTime("timestamp", "cadence", self, "max_cadence", "average_cadence"),
                 MaximizeAndAverageOverTime("timestamp", "torque", self, "max_torque", "average_torque"),
                 MaximizeAndAverageOverTime("timestamp", "power", self, "max_power", "average_power"),
                 self
                 ))
        return ret

    def analyze(self):
        self.set_max_power(self.max_power)

    def init_reducer(self):
        self.rollingwindow = []
        self.count = 0
        self.sum_norm = 0
        self.starttime = None
        self.timediff = 0

    def reduce(self, wp):
        if self.starttime is None:
            self.starttime = wp.timestamp
        self.timediff = (wp.timestamp - self.starttime).seconds
        self.rollingwindow.append((wp.timestamp, wp.power))
        while (wp.timestamp - self.rollingwindow[0][0]).seconds > 30:
            del self.rollingwindow[0]
        diff = (wp.timestamp - self.rollingwindow[0][0]).seconds
        if diff >= 29:
            prev = None
            s = 0
            for p in self.rollingwindow:
                td = (p[0] - prev[0]).seconds if prev else 1
                prev = p
                s += p[1] * td
                self.sum_norm += (round(s / diff)) ** 4
                self.count += 1
        return self

    def reduction(self):
        if self.count > 0 and self.sum_norm > 0:
            self.normalized_power = int(round((self.sum_norm / self.count) ** (0.25)))
            self.vi = round(self.normalized_power / self.average_power, 2)
            ftp = self.get_ftp()
            if ftp:
                self.intensity_factor = round(self.normalized_power / ftp, 2) if ftp > 0 else 0
                self.tss = (self.timediff * self.intensity_factor ** 2) / 36 if ftp > 0 else 0


class RunPace(grumble.Model, Reducer):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPace)
    timestamp = grumble.TimeDeltaProperty()
    speed = grumble.IntegerProperty()

    def init_reducer(self):
        self.rollingwindow = []
        self.starttime = None
        self.max_speed = None

    def reduce(self, wp):
        if wp.distance is None:
            return self
        self.rollingwindow.append((wp.distance, wp.timestamp))
        while self.rollingwindow and (wp.distance - self.rollingwindow[0][0]) > self.cpdef.distance:
            del self.rollingwindow[0]
        dist = wp.distance - self.rollingwindow[0][0]
        td = wp.timestamp - self.rollingwindow[0][1]
        if td:
            speed = int(round(dist / td.seconds))
            if self.max_speed is None or speed > self.max_speed:
                self.max_speed = speed
                self.starttime = self.rollingwindow[0][1]
        return self

    def reduction(self):
        if self.starttime is not None:
            self.speed = self.max_speed
            self.timestamp = self.starttime
            self.put()

    def after_store(self):
        best = None
        q = BestRunPace.query(parent = self.cpdef).add_sort("snapshotdate")
        q.add_filter("snapshotdate <= ", self.parent()().get_session().start_time)
        best = q.get()
        if not best or self.speed > best.speed:
            best = BestRunPace(parent = self.cpdef)
            best.best = self
            best.speed = self.speed
            best.put()


class BestRunPace(grumble.Model):
    snapshotdate = grumble.DateTimeProperty(auto_now_add = True)
    best = grumble.ReferenceProperty(RunPace)
    speed = grumble.FloatProperty(default = 0)  # m/s


class RunPart(IntervalPart):
    average_cadence = grumble.IntegerProperty(default = 0)  # rpm
    max_cadence = grumble.IntegerProperty(default = 0)  # rpm

    def reducers(self):
        ret = []
        for cpdef in self.get_activityprofile().get_all_linked_references(sweattrails.config.CriticalPace):
            if cpdef.distance <= self.get_interval().distance:
                p = RunPace(parent = self)
                p.cpdef = cpdef
                p.put()
                ret.append(p)
        ret.append(MaximizeAndAverageOverTime("timestamp", "cadence", self, "max_cadence", "average_cadence"))
        return ret

class SwimPart(IntervalPart):
    pass

class SessionTypeReference(grumble.reference.ReferenceProperty):
    def __init__(self, *args, **kwargs):
        kwargs["reference_class"] = sweattrails.config.SessionType
        super(SessionTypeReference, self).__init__(*args, **kwargs)

    def get_interval_part_type(self, sessiontype, interval):
        return sessiontype.get_interval_part_type(interval.get_activityprofile())

    def after_set(self, session, old_sessiontype, new_sessiontype):
        if not old_sessiontype or (old_sessiontype.name != new_sessiontype.name):
            t = self.get_interval_part_type(new_sessiontype, session)
            sameparttype = False
            if session.intervalpart:
                if isinstance(session.intervalpart, t):
                    sameparttype = True
                else:
                    part = session.intervalpart
                    session.intervalpart = None
                    grumble.delete(part)
            for i in Interval.query(ancestor = session):
                if i.intervalpart and not isinstance(i.intervalpart, t):
                    part = i.intervalpart
                    i.intervalpart = None
                    grumble.delete(part)
                    i.put()
            if t and not sameparttype:
                part = t(parent = session)
                part.put()
                session.intervalpart = part
                for i in Interval.query(ancestor = session):
                    if i.intervalpart:
                        part = i.intervalpart
                        i.intervalpart = None
                        grumble.delete(part)
                    part = t(parent = i)
                    part.put()
                    i.intervalpart = part
                    i.put()


class GeoData(grumble.Model):
    max_elev = grumble.IntegerProperty(default = -100)  # In meters
    min_elev = grumble.IntegerProperty(default = 10000)  # In meters
    elev_gain = grumble.IntegerProperty(default = 0)  # In meters
    elev_loss = grumble.IntegerProperty(default = 0)  # In meters
    bounding_box = grumble.geopt.GeoBoxProperty()


@grumble.property.transient
class AvgSpeedProperty(grumble.property.FloatProperty):
    def getvalue(self, instance):
        return instance.distance / instance.duration.seconds

    def setvalue(self, instance, value):
        pass


class Interval(grumble.Model, Reducer):
    interval_id = grumble.property.StringProperty(is_key = True)
    intervalpart = grumble.reference.ReferenceProperty(IntervalPart)
    timestamp = grumble.property.TimeDeltaProperty(verbose_name = "Start at")
    elapsed_time = grumble.property.TimeDeltaProperty(verbose_name = "Elapsed time")  # Duration including pauses
    duration = grumble.property.TimeDeltaProperty(verbose_name = "Duration")  # Time excluding pauses
    distance = grumble.property.IntegerProperty(default = 0)  # Distance in meters
    average_hr = grumble.property.IntegerProperty(default = 0, verbose_name = "Avg. Heartrate")  # bpm
    max_hr = grumble.property.IntegerProperty(default = 0, verbose_name = "Max. Heartrate")  # bpm
    average_speed = AvgSpeedProperty(verbose_name = "Avg. Speed/Pace")
    max_speed = grumble.property.FloatProperty(default = 0, verbose_name = "Max. Speed/Pace")  # m/s
    work = grumble.property.IntegerProperty(default = 0)  # kJ
    calories_burnt = grumble.property.IntegerProperty(default = 0)  # kJ

    def after_insert(self):
        sessiontype = self.get_sessiontype()
        if sessiontype:
            partcls = sessiontype.get_interval_part_type(self.get_activityprofile())
            if partcls:
                part = partcls(parent = self)
                part.put()
                self.intervalpart = part
                self.put()

    def analyze(self):
        reducers = Reducers()
        part = self.intervalpart
        reducers.append(MaximizeAndAverageOverTime("timestamp", "heartrate", self, "max_hr", "average_hr"))
        reducers.append(Maximize("speed", self, "max_speed"))
        if part:
            reducers.extend(part.reducers())
        reducers.append(self)
        reducers.reduce(self.waypoints())
        if part:
            part.put()
        self.put()

        if part:
            part.analyze()
        for i in Interval.query(parent = self):
            i.analyze()

    def init_reducer(self):
        self.cur_altitude = None
        self.bounding_box = None
        self.elev_gain = 0
        self.elev_loss = 0
        self.min_elev = None
        self.max_elev = None

    def reduce(self, wp):
        alt = wp.altitude
        if alt is not None:
            if self.cur_altitude is not None:
                if alt > self.cur_altitude:
                    self.elev_gain += (alt - self.cur_altitude)
                else:
                    self.elev_loss += (self.cur_altitude - alt)
            self.min_elev = min(self.min_elev, alt)
            self.max_elev = min(self.max_elev, alt)
            self.cur_altitude = alt
        if wp.location is not None:
            if self.bounding_box is not None:
                self.bounding_box.extend(wp.location)
            else:
                self.bounding_box = grumble.geopt.GeoBox(wp.location, wp.location)
        return self

    def reduction(self):
        if self.cur_altitude is not None or self.bounding_box is not None:
            geodata = GeoData(parent = self)
            if self.cur_altitude is not None:
                geodata.max_elev = self.max_elev
                geodata.min_elev = self.min_elev
                geodata.elev_gain = self.elev_gain
                geodata.elev_loss = self.elev_loss
            if self.bounding_box:
                geodata.bounding_box = grumble.geopt.GeoBox(self.bounding_box)
            geodata.put()

    def get_session(self):
        return self.root()

    def get_intervals(self):
        return Interval.query(parent = self)

    def get_geodata(self):
        return GeoData.query(parent = self).get()

    def waypoints(self):
        session = self.get_session()
        q = Waypoint.query(parent = session)
        q.add_sort("timestamp")
        q.add_filter("timestamp", " >= ", self.timestamp)
        q.add_filter("timestamp", " < ", self.timestamp + self.elapsed_time)
        return q

    def get_sessiontype(self):
        return self.get_session().sessiontype

    def get_athlete(self):
        return self.get_session().athlete

    def get_activityprofile(self):
        athlete = self.get_athlete()
        return sweattrails.config.ActivityProfile.get_profile(athlete)

    def on_delete(self):
        GeoData.query(parent = self).delete()
        IntervalPart.query(parent = self).delete()
        Interval.query(parent = self).delete()


class Session(Interval):
    athlete = grumble.ReferenceProperty(grizzle.User)
    description = grumble.StringProperty()
    sessiontype = SessionTypeReference()
    start_time = grumble.DateTimeProperty(verbose_name = "Date/Time")
    notes = grumble.StringProperty(multiline = True)
    posted = grumble.DateTimeProperty(auto_now_add = True, verbose_name = "Posted on")
    inprogress = grumble.BooleanProperty(default = True)
    device = grumble.StringProperty(default = "")

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
    timestamp = grumble.TimeDeltaProperty()
    location = grumble.geopt.GeoPtProperty()
    altitude = grumble.IntegerProperty()  # meters
    speed = grumble.FloatProperty(default = 0.0)  # m/s
    distance = grumble.IntegerProperty(default = 0)  # meters
    cadence = grumble.IntegerProperty(default = 0)
    heartrate = grumble.IntegerProperty(default = 0)
    power = grumble.IntegerProperty(default = 0)
    torque = grumble.FloatProperty(default = 0)
    temperature = grumble.IntegerProperty(default = 0)

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

