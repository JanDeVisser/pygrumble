# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Oct-2013 8:37:08 AM$"

import bisect
import datetime
import json
import time

import gripe
import grizzle
import grumble
import grumble.geopt
import grumble.property
import grumble.reference
import srtm
import sweattrails.config
import sweattrails.userprofile

logger = gripe.get_logger(__name__)


class Reducer(object):
    def init_reducer(self):
        pass

    def reduce(self, value):
        pass

    def reduction(self):
        pass


class Reducers(list):
    def reduce(self, iterable):
        self.total_c = time.clock()
        def run(reducers, item):
            for r in reducers:
                c = time.clock()
                r.reduce(item)
                r.clock += time.clock() - c
            return reducers
        
        self.init_c = time.clock()
        for r in self:
            r.init_reducer()
            r.clock = 0.0
        self.init_c = time.clock() - self.init_c
        
        self.reduce_c = time.clock()
        reduce(run, iterable, self)
        self.reduce_c = time.clock() - self.reduce_c
        
        self.done_c = time.clock()
        for r in self:
            r.reduction()
        self.done_c = time.clock() - self.done_c
        self.total_c = time.clock() - self.total_c
        self.report()
        
    def report(self):
        rep = """
=================================================
  R E D U C T I O N  R E P O R T
-------------------------------------------------
#Reducers:                              {:d}
init_reducer() [Total]                  {:.6f}
{:s}
reduce() [Total]                        {:.6f}
reduction() [Total]                     {:.6f}
=================================================
Total                                   {:.6f}
-------------------------------------------------
""".format(len(self), self.init_c,
           "\n".join([
"{:40.40s}{:6f}".format(r, r.clock) for r in self]),
           self.reduce_c, self.done_c, self.total_c)
        logger.debug(rep)


class SimpleReducer(Reducer):
    def __init__(self, item_prop, target, aggr_prop):
        self.item_prop = item_prop
        self.aggr_prop = aggr_prop
        self.target = target
        self.cur = None
        self.count = 0
        
    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.item_prop)

    def reduce(self, item):
        value = getattr(item, self.item_prop)
        self.cur = self.reducevalue(value)
        self.count += 1

    def reduction(self):
        finalvalue = self.finalize()
        setattr(self.target, self.aggr_prop, finalvalue)

    def finalize(self):
        return self.cur


class Accumulate(SimpleReducer):
    def reducevalue(self, value):
        return ((self.cur if self.cur is not None else 0) + 
                (value if value else 0))


class AverageOverSamples(Accumulate):
    def finalize(self):
        return int(round(self.cur / self.count)) if self.count > 0 else 0


class AverageOverTime(SimpleReducer):
    def __init__(self, item_timestamp, item_prop, target, aggr_prop):
        super(AverageOverTime, self).__init__(item_prop, target, aggr_prop)
        self.item_timestamp = item_timestamp
        self.starttime = None
        self.lasttime = None

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
        self.count += 1
        self.lasttime = ts

    def finalize(self):
        diff = (self.lasttime - self.starttime).seconds
        return int(round(self.cur) / diff) if diff > 0 else 0


class Maximize(SimpleReducer):
    def reducevalue(self, value):
        return max(self.cur, value) or 0


class Minimize(SimpleReducer):
    def reducevalue(self, value):
        return min(self.cur, value) or 0


class UpdatePolicy():
    DONT_UPDATE, UPDATE_WITH_OFFSET, UPDATE_ABSOLUTE = range(3)

    def __init__(self, distance, duration):
        self.distance = distance
        self.duration = duration


@grumble.abstract
class Timestamped(object):
    def __getattr__(self, name):
        if name == "seconds":
            if not hasattr(self, "_seconds"):
                self._seconds = self.timestamp.seconds
            return self._seconds
        raise AttributeError(name)


    def __cmp__(self, other):
        return (
            self.seconds - other.seconds
            if hasattr(other, "seconds")
            else self.seconds - other.timestamp.seconds
                if hasattr(other, "timestamp")
                else self.seconds - other
        )


@grumble.abstract
class IntervalPart(grumble.Model):
    def _get_date(self):
        return self.get_session().start_time

    def get_interval(self):
        return self.parent()

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


class RollingWindow(list):
    def __init__(self, min_precision):
        self._running_sum = 0.0
        self.min_precision = min_precision
        
    def append(self, e):
        self._running_sum += e.term()
        super(RollingWindow, self).append(e)
        last = None
        while self.span() > self.max_span():
            last = self.pop(0)
        if last:
            if self.precision(last) < self.precision(self[0]):
                self.insert(0, last)
                self._running_sum += last.term()
        
    def pop(self, ix):
        e = super(RollingWindow, self).pop(ix)
        self._running_sum -= e.term()
        return e
    
    def precision(self, e = None):
        if e is None:
            e = self[0]
        return abs(self[-1].offset() - e.offset() - self.max_span())
    
    def span(self):
        return self[-1].offset() - self[0].offset()
    
    def valid(self):
        if len(self) < 2:
            return False
        return self.precision() <= self.min_precision

    def _result(self):
        return self._running_sum / self.span() 
    
    def result(self):
        return self._result() if self.valid() else None

    
class TimeWindow(RollingWindow):
    def __init__(self, duration, min_precision = 1):
        super(TimeWindow, self).__init__(min_precision)
        self.duration = duration
    
    def max_span(self):
        return self.duration
    
    
class TimeWindowEntry(object):
    def __init__(self, waypoint, term):
        self.seconds = waypoint.timestamp.seconds
        self._term = term or 0
        self.timestamp = waypoint.timestamp
        self.distance = waypoint.distance
        
    def offset(self):
        return self.seconds
        
    def term(self):
        return self._term


class CriticalPowerReducer(Reducer):
    def __init__(self, cp):
        self.cp = cp
        self.duration = cp.cpdef.duration.seconds
        
    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.cp.cpdef.duration)

    def init_reducer(self):
        self.window = TimeWindow(self.duration)
        self.starttime = None
        self.max_avg = None

    def reduce(self, wp):
        self.window.append(TimeWindowEntry(wp, wp.power))
        avg = self.window.result()
        if avg and (self.max_avg is None or avg > self.max_avg):
            self.max_avg = avg
            self.starttime = self.window[0].timestamp

    def reduction(self):
        if self.starttime is not None:
            self.cp.power = self.max_avg
            self.cp.timestamp = self.starttime - self.cp.parent().get_interval().timestamp
            self.cp.put()


class CriticalPower(grumble.Model, Timestamped):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPowerInterval)
    timestamp = grumble.TimeDeltaProperty()
    power = grumble.IntegerProperty()

    def after_store(self):
        q = BestCriticalPower.query(parent = self.cpdef).add_sort("snapshotdate")
        q.add_filter("snapshotdate <= ", self.parent().get_session().start_time)
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


@grumble.property.transient
class AvgSpeedProperty(grumble.property.FloatProperty):
    def getvalue(self, instance):
        if not instance.distance or \
           not instance.duration:
            return 0.0
        else:
            if isinstance(instance.duration, datetime.timedelta):
                if not instance.duration.seconds:
                    return 0.0
                else:
                    duration = instance.duration.seconds
            else:
                duration = instance.duration
            return float(instance.distance) / float(duration)

    def setvalue(self, instance, value):
        pass


@grumble.property.transient
class WattsPerKgProperty(grumble.FloatProperty):
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
                    ret = float(power) / weight
        return ret

    def setvalue(self, instance, value):
        pass


@grumble.property.transient
class VIProperty(grumble.property.FloatProperty):
    def __init__(self, **kwargs):
        super(VIProperty, self).__init__(**kwargs)

    def getvalue(self, instance):
        np = float(instance.normalized_power or 0.0)
        ap = float(instance.average_power or 0.0)
        return round(np / ap, 2) if ap and np else 0.0

    def setvalue(self, instance, value):
        pass


@grumble.property.transient
class IFProperty(grumble.property.FloatProperty):
    def __init__(self, **kwargs):
        super(IFProperty, self).__init__(**kwargs)
 
    def getvalue(self, instance):
        ftp = instance.get_ftp()
        np = float(instance.normalized_power or 0.0)
        return round(np / ftp, 2) if ftp and ftp > 0 else 0

    def setvalue(self, instance, value):
        pass


@grumble.property.transient
class TSSProperty(grumble.property.FloatProperty):
    def __init__(self, **kwargs):
        super(TSSProperty, self).__init__(**kwargs)
 
    def getvalue(self, instance):
        return (instance.parent().duration.seconds * (instance.intensity_factor ** 2)) / 36

    def setvalue(self, instance, value):
        pass


class NormalizedPowerReducer(Reducer):
    class NPWindow(TimeWindow):
        def __init__(self):
            super(NormalizedPowerReducer.NPWindow, self).__init__(30)
            
        def _result(self):
            return (self._running_sum / self.span())**4 
        
    def __init__(self, bikepart):
        self.bikepart = bikepart
        
    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def init_reducer(self):
        self.window = NormalizedPowerReducer.NPWindow()
        self.count = 0
        self.sum_norm = 0

    def reduce(self, wp):
        self.window.append(TimeWindowEntry(wp, wp.power))
        np_term = self.window.result()
        if np_term:
            self.sum_norm += np_term
            self.count += 1

    def reduction(self):
        if self.count > 0 and self.sum_norm > 0:
            self.bikepart.normalized_power = int(round((self.sum_norm / self.count) ** (0.25)))
        else:
            self.bikepart.normalized_power = 0

    
class BikePart(IntervalPart):
    average_power = grumble.IntegerProperty(verbose_name = "Average Power", default = 0, suffix = "W")  # W
    average_watts_per_kg = WattsPerKgProperty(powerproperty = "average_power", suffix = "W/kg")
    normalized_power = grumble.IntegerProperty(verbose_name = "Normalized Power", suffix = "W")  # W
    normalized_watts_per_kg = WattsPerKgProperty(powerproperty = "normalized_power", suffix = "W/kg")
    max_power = grumble.IntegerProperty(verbose_name = "Maximum Power", default = 0, suffix = "W")  # W
    max_watts_per_kg = WattsPerKgProperty(powerproperty = "max_power", suffix = "W/kg")
    average_cadence = grumble.IntegerProperty(verbose_name = "Average Cadence", default = 0, suffix = "rpm")  # rpm
    max_cadence = grumble.IntegerProperty(verbose_name = "Maximum Cadence", default = 0, suffix = "rpm")  # rpm
    average_torque = grumble.FloatProperty(verbose_name = "Average Torque", default = 0.0, suffix = "Nm")  # Nm
    max_torque = grumble.FloatProperty(verbose_name = "Maximum Torque", default = 0.0, suffix = "Nm")  # Nm
    vi = VIProperty(verbose_name = "VI", default = 0.0)
    intensity_factor = IFProperty(verbose_name = "IF", default = 0.0)
    tss = TSSProperty(verbose_name = "TSS", default = 0.0)

    def get_ftp(self):
        if not hasattr(self, "_ftp"):
            interval = self.parent()()
            athlete = interval.get_athlete()
            bikepart = sweattrails.userprofile.BikeProfile.get_userpart(athlete)
            self._ftp = bikepart.get_ftp(self.get_date()) if bikepart is not None else 0
        return self._ftp

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
                ret.append(CriticalPowerReducer(cp))

        ret.extend([
            Maximize("torque", self, "max_torque"),
            AverageOverTime("timestamp", "torque", self, "average_torque"),
            Maximize("cadence", self, "max_cadence"),
            AverageOverTime("timestamp", "cadence", self, "average_cadence"),
            Maximize("power", self, "max_power"),
            AverageOverTime("timestamp", "power", self, "average_power"),
            NormalizedPowerReducer(self)
        ])
        return ret

    def analyze(self):
        self.set_max_power(self.max_power)


class RunPaceWindow(RollingWindow):
    def __init__(self, distance, min_precision = 10):
        super(RunPaceWindow, self).__init__(min_precision)
        self.distance = distance
    
    def max_span(self):
        return self.distance
    
    def _result(self):
        return self[-1].seconds - self[0].seconds 

    
class RunPaceWindowEntry(object):
    def __init__(self, waypoint):
        self.seconds = waypoint.timestamp.seconds
        self.distance = waypoint.distance
        self.timestamp = waypoint.timestamp
        
    def offset(self):
        return self.distance
        
    def term(self):
        return 1


class RunPaceReducer(Reducer):
    def __init__(self, runpace):
        self.runpace = runpace
        self.distance = runpace.cpdef.distance
    
    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.distance)

    def init_reducer(self):
        self.window = RunPaceWindow(self.distance)
        self.starttime = None
        self.atdistance = None
        self.duration = None

    def reduce(self, wp):
        if wp.distance is None:
            return
        self.window.append(RunPaceWindowEntry(wp))
        duration = self.window.result()
        if duration and (self.duration is None or duration < self.duration):
            self.duration = duration
            self.starttime = self.window[0].timestamp
            self.atdistance = self.window[0].distance

    def reduction(self):
        if self.starttime is not None:
            self.runpace.duration = self.duration
            self.runpace.timestamp = self.starttime - self.runpace.parent().get_interval().timestamp
            self.runpace.atdistance = self.atdistance # FIXME - Offset w/ start of interval
            self.runpace.put()


class RunPace(grumble.Model, Timestamped):
    cpdef = grumble.reference.ReferenceProperty(sweattrails.config.CriticalPace)
    timestamp = grumble.property.TimeDeltaProperty()
    atdistance = grumble.property.IntegerProperty()
    distance = grumble.property.IntegerProperty()
    duration = grumble.property.IntegerProperty()
    speed = AvgSpeedProperty()

    def after_store(self):
        logger.debug("RunPace.after_store: %s in %s", self.cpdef.name, self.duration)
        if (self.duration > 0) and Session.samekind(self.parent().get_interval()):

            # See if this is a record at this time, i.e. if there is no 
            # faster entry dated before this session: 
            q = BestRunPace.query(parent = self.cpdef).add_sort("snapshotdate")
            q.add_filter("snapshotdate <= ", self.parent().get_session().start_time)
            q.add_filter("duration < ", self.duration)
            best = q.get()
            if not best:
                logger.debug("RunPace.after_store: this is a record")
                best = BestRunPace(parent = self.cpdef)
                best.cpdef = self.cpdef
                best.snapshotdate = self.parent().get_session().start_time
                best.best = self
                best.duration = self.duration
                best.distance = self.distance
                best.put()
            else:
                logger.debug("RunPace.after_store: didn't beat existing record -> %s in %s", self.cpdef.name, best.duration)

            # Delete records set after this session that are not as good
            # as this one. This can happen if old sessions are imported.
            q = BestRunPace.query(parent = self.cpdef).add_sort("snapshotdate")
            q.add_filter("snapshotdate > ", self.parent().get_session().start_time)
            q.add_filter("duration <= ", self.duration)
            for brp in q:
                logger.debug("RunPace.after_store: cleaning up superceded record %s in %s", self.cpdef.name, brp.duration)
            q.delete()
        else:
            logger.debug("RunPace.after_store: skipping, %s", self.parent().get_interval().__class__.__name__)


class BestRunPace(grumble.Model):
    cpdef = grumble.ReferenceProperty(sweattrails.config.CriticalPace)
    snapshotdate = grumble.DateTimeProperty(auto_now_add = True)
    best = grumble.ReferenceProperty(RunPace)
    distance = grumble.IntProperty()
    duration = grumble.IntegerProperty()
    speed = AvgSpeedProperty()


class RunPart(IntervalPart):
    average_cadence = grumble.IntegerProperty(default = 0, suffix = "strides/min")  # rpm
    max_cadence = grumble.IntegerProperty(default = 0, suffix = "strides/min")  # rpm

    def reducers(self):
        ret = []
        for cpdef in self.get_activityprofile().get_all_linked_references(sweattrails.config.CriticalPace):
            if cpdef.distance <= self.get_interval().distance:
                p = RunPace(parent = self)
                p.cpdef = cpdef
                p.distance = cpdef.distance
                ret.append(RunPaceReducer(p))
        ret.extend([
            Maximize("cadence", self, "max_cadence"),
            AverageOverTime("timestamp", "cadence", self, "average_cadence")])
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
    max_elev = grumble.IntegerProperty(default = -100, verbose_name = "Max. Elevation")  # In meters
    min_elev = grumble.IntegerProperty(default = 10000, verbose_name = "Min. Elevation")  # In meters
    elev_gain = grumble.IntegerProperty(default = 0, verbose_name = "Elevation Gain")  # In meters
    elev_loss = grumble.IntegerProperty(default = 0, verbose_name = "Elevation Loss")  # In meters
    bounding_box = grumble.geopt.GeoBoxProperty()
    
    def get_session(self):
        return self.parent().get_session()


class GeoReducer(Reducer):
    def __init__(self, interval):
        self.interval = interval

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def init_reducer(self):
        self.cur_elev = None
        self.bounding_box = None
        self.elev_gain = 0
        self.elev_loss = 0
        self.min_elev = 20000
        self.max_elev = None
        self.elev_data = srtm.get_data()
        self.updated = []

    def reduce(self, wp):
        wp.corrected_elevation = None
        if wp.location is not None:
            if self.bounding_box is None:
                self.bounding_box = grumble.geopt.GeoBox()
            self.bounding_box.extend(wp.location)
            wp.corrected_elevation = self.elev_data.get_elevation(wp.location.lat, wp.location.lon)
            if wp.corrected_elevation is not None:
                self.updated.append(wp)
        elev = wp.corrected_elevation if wp.corrected_elevation is not None else wp.elevation
        if elev is not None:
            if self.cur_elev is not None:
                if elev > self.cur_elev:
                    self.elev_gain += (elev - self.cur_elev)
                else:
                    self.elev_loss += (self.cur_elev - elev)
            self.min_elev = min(self.min_elev, elev)
            self.max_elev = max(self.max_elev, elev)
            self.cur_elev = elev
        return self

    def reduction(self):
        if self.cur_elev is not None or self.bounding_box is not None:
            geodata = GeoData(parent = self.interval)
            if self.cur_elev is not None:
                geodata.max_elev = self.max_elev
                geodata.min_elev = self.min_elev
                geodata.elev_gain = self.elev_gain
                geodata.elev_loss = self.elev_loss
            if self.bounding_box:
                geodata.bounding_box = grumble.geopt.GeoBox(self.bounding_box)
            geodata.put()
            self.interval.geodata = geodata
        for wp in self.updated:
            wp.put()


class Interval(grumble.Model, Timestamped):
    interval_id = grumble.property.StringProperty(is_key = True)
    timestamp = grumble.property.TimeDeltaProperty(verbose_name = "Start at")
    intervalpart = grumble.reference.ReferenceProperty(IntervalPart)
    geodata = grumble.reference.ReferenceProperty(GeoData)
    elapsed_time = grumble.property.TimeDeltaProperty()  # Duration including pauses
    duration = grumble.property.TimeDeltaProperty()  # Time excluding pauses
    distance = grumble.property.IntegerProperty(default = 0)  # Distance in meters
    average_heartrate = grumble.property.IntegerProperty(default = 0, verbose_name = "Avg. Heartrate")  # bpm
    max_heartrate = grumble.property.IntegerProperty(default = 0, verbose_name = "Max. Heartrate")  # bpm
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

    def analyze(self, callback = None):
        reducers = Reducers()
        part = self.intervalpart
        logger.debug("Interval.analyze(): Getting subintervals")
        intervals = Interval.query(parent = self).fetchall()
        num = len(intervals) + (1 if part else 2)
        ix = 0
        if callback:
            callback(int((float(ix) / float(num)) * 100.0))
        logger.debug("Interval.analyze(): Getting reducers")
        reducers.extend([
            Maximize("heartrate", self, "max_hr"),
            AverageOverTime("timestamp", "heartrate", self, "average_hr"),
            Maximize("speed", self, "max_speed"),
            GeoReducer(self)
        ])
        if part:
            reducers.extend(part.reducers())
        logger.debug("Interval.analyze(): Getting waypoints")
        wps = self.waypoints()
        logger.debug("Interval.analyze(): Reducing")
        reducers.reduce(wps)
        logger.debug("Interval.analyze(): Done reducing")
        if part:
            logger.debug("Interval.analyze(): Storing part")
            part.put()
            logger.debug("Interval.analyze(): Storing self")
        self.put()

        if part:
            ix += 1
            if callback:
                callback(int((float(ix) / float(num)) * 100.0))
            logger.debug("Interval.analyze(): Analyzing part")
            part.analyze()
        for i in intervals:
            ix += 1
            logger.debug("Interval.analyze(): Analyzing interval %d/%d", ix - 1, num - 2)
            if callback:
                callback(int((float(ix) / float(num)) * 100.0))
            i.analyze()

    def get_session(self):
        return self.root()

    def get_intervals(self):
        return Interval.query(parent = self)

    def get_geodata(self):
        return GeoData.query(parent = self).get()

    def waypoints(self, allwps = None):
        if not hasattr(self, "_wps"):
            allwps = allwps or self.parent().waypoints()
            end_ts = (self.timestamp + self.elapsed_time).seconds
            first = bisect.bisect_left(allwps, self)
            last = bisect.bisect_right(allwps, end_ts)
            self._wps = allwps[first:last] if first >= 0 and last >= 0 else []
        return self._wps

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
    athlete = grumble.reference.ReferenceProperty(grizzle.User)
    description = grumble.property.StringProperty()
    sessiontype = SessionTypeReference()
    start_time = grumble.property.DateTimeProperty(verbose_name = "Date/Time")
    notes = grumble.property.StringProperty(multiline = True)
    posted = grumble.property.DateTimeProperty(auto_now_add = True, verbose_name = "Posted on")
    inprogress = grumble.property.BooleanProperty(default = True)
    device = grumble.property.StringProperty(default = "")
    
    def after_insert(self):
        super(Session, self).after_insert()
        athlete = self.athlete
        userprofile = sweattrails.userprofile.UserProfile.get_userpart(athlete)
        userprofile.uploads += 1
        userprofile.last_upload = datetime.datetime.now()
        userprofile.put()

    def waypoints(self, allwps = None):
        if not hasattr(self, "_wps"):
            if allwps:
                self._wps = allwps
            else:
                q = Waypoint.query(parent = self, keys_only = False)
                q.add_sort("timestamp")
                self._wps = q.fetchall()
        return self._wps

    def upload_slice(self, request):
        lines = request.get("slice").splitlines()
        for line in lines:
            if (line.strip() == ''):
                continue
            wp = Waypoint(parent = self)
            wp.session = self
            (seqnr, lat, lon, speed, timestamp, altitude, distance) = line.split(";")
            wp.seqnr = int(seqnr)
            wp.location = grumble.geopt.GeoPt(float(lat), float(lon))
            wp.speed = float(speed)
            wp.timestamp = datetime.datetime.fromtimestamp(int(timestamp) // 1000)
            wp.elevation = float(altitude)
            wp.distance = float(distance)
            wp.put()

    def commit(self):
        self.inprogress = False
        self.put()

    def on_delete(self):
        super(Session, self).on_delete()
        Waypoint.query(ancestor = self).delete()


class Waypoint(grumble.Model, Timestamped):
    timestamp = grumble.property.TimeDeltaProperty()
    location = grumble.geopt.GeoPtProperty()
    elevation = grumble.property.FloatProperty(default = 0)  # meters
    corrected_elevation = grumble.property.IntegerProperty(default = 0)  # meters
    speed = grumble.property.FloatProperty(default = 0.0)  # m/s
    distance = grumble.property.IntegerProperty(default = 0)  # meters
    cadence = grumble.property.IntegerProperty(default = 0)
    heartrate = grumble.property.IntegerProperty(default = 0)
    power = grumble.property.IntegerProperty(default = 0)
    torque = grumble.property.FloatProperty(default = 0)
    temperature = grumble.property.IntegerProperty(default = 0)

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

