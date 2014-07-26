#!/usr/bin/python

import datetime
import sys
import time

import gripe.db
import grizzle
import grumble.geopt
import sweattrails.config
import sweattrails.session

from fitparse import Activity, FitParseError

def local_date_to_utc(d):
    """Local date to UTC"""
    return datetime.datetime.utcfromtimestamp(time.mktime(d.timetuple()))

def semicircle_to_degrees(semicircles):
    """Convert a number in semicricles to degrees"""
    return semicircles * (180.0 / 2.0 ** 31)


class RecordWrapper(object):
    def __init__(self, rec):
        self._data = rec.as_dict(True)
        self._fitrec = rec
        self._grumble_obj = None
        self.container = None
        self.initialize()

    def initialize(self):
        pass

    def fitrecord(self):
        return self._fitrec

    def object(self, obj = None):
        if obj is not None:
            self._grumble_obj = obj
        return self._grumble_obj

    def __call__(self):
        return self.object()

    def get_data(self, key):
        assert "RecordWrapper.get_data(%s): no FIT record set in class %s" % (key, self.__class__)
        return self.fitrecord().get_data(key)

    def log(self, msg):
        if self.container is not None:
            self.container.log(msg)

    @classmethod
    def create(cls, container, rec):
        ret = None
        if rec.type.name == 'session':
            ret = FITSession(rec)
            container.add_session(ret)
        elif rec.type.name == 'lap':
            ret = FITLap(rec)
            container.add_lap(ret)
        elif rec.type.name == 'record':
            ret = FITRecord(rec)
            container.add_record(ret)
        return ret

class FITLap(RecordWrapper):
    def convert_interval(self, interval):
        self.start_time = self.get_data("start_time")
        interval.interval_id = str(local_date_to_utc(self.start_time)) + "Z"
        ts = self.start_time - self.session.start_time
        interval.timestamp = ts
        interval.distance = self.get_data("total_distance")
        interval.elapsed_time = self.get_data("total_elapsed_time")
        interval.duration = self.get_data("total_timer_time")
        interval.calories_burnt = self.get_data("total_calories")
        interval.put()
        return interval

class FITRecord(RecordWrapper):
    def convert(self, session):
        wp = sweattrails.session.Waypoint(parent = session)
        wp.timestamp = self.get_data("timestamp") - self.session.start_time
        lat = self.get_data("position_lat")
        lon = self.get_data("position_long")
        if lat and lon:
            wp.location = grumble.geopt.GeoPt(
                semicircle_to_degrees(lat), semicircle_to_degrees(lon))
        wp.speed = self.get_data("speed")
        wp.altitude = self.get_data("altitude")
        wp.distance = self.get_data("distance")
        wp.cadence = self.get_data("cadence")
        wp.heartrate = self.get_data("heart_rate")
        wp.power = self.get_data("power")
        wp.torque = 0  # FIT doesn't seem to have torque.
        wp.temperature = self.get_data("temperature")
        wp.put()
        return wp

class FITSession(FITLap):
    def initialize(self):
        self.start = self.get_data("start_time")
        self.end = self.get_data("timestamp")
        self.laps = []
        self.records = []
        self.session = self

    def contains(self, obj):
        return self.start < obj._data["timestamp"] <= self.end

    def add_lap(self, lap):
        self.laps.append(lap)
        lap.session = self

    def add_record(self, record):
        self.records.append(record)
        record.session = self

    def convert(self, athlete):
        with gripe.db.Tx.begin():
            assert athlete, "fitparse.upload(): athlete is None"
            session = sweattrails.session.Session()
            session.athlete = athlete
            self.start_time = self.get_data("start_time")
            session.start_time = self.start_time
            session.inprogress = False
            profile = sweattrails.config.ActivityProfile.get_profile(athlete)
            assert profile, "fitparse.upload(): User %s has no profile" % athlete.uid()
            sessiontype = profile.get_default_SessionType(self.get_data("sport"))
            assert sessiontype, "fitparse.upload(): User %s has no default session type for sport %s" % (athlete.uid(), self.get_data("sport"))
            session.sessiontype = sessiontype
            self.log("Converting session %s/%s" % (self.index, len(self.container.sessions)))
            self.convert_interval(session)
            self.log("Session %s/%s: Converting %s intervals" % (self.index, len(self.container.sessions), len(self.laps)))
            for lap in self.laps:
                interval = sweattrails.session.Interval(parent = session)
                lap.convert_interval(interval)
            self.log("Session %s/%s: Converting %s waypoints" % (self.index, len(self.container.sessions), len(self.records)))
            for record in self.records:
                record.convert(session)
            self.log("Analyzing session %s/%s" % (self.index, len(self.container.sessions)))
            session.analyze()
            return session

class FITParser(object):
    def __init__(self, user, filename):
        self.user = user
        self.filename = filename
        self.activity = None
        self.sessions = []
        self.laps = []
        self.records = []
        self.logger = None
        
    def setLogger(self, logger):
        self.logger = logger
        
    def parse(self):
        self.log("Reading FIT file %s" % self.filename)
        self.activity = Activity(self.filename)
        self.log("Parsing FIT file %s" % self.filename)
        self.activity.parse()
        self.log("Processing FIT file %s" % self.filename)
        self._process()
        self.log("FIT file %s converted" % self.filename)
        return None
    
    def log(self, msg):
        if self.logger is not None:
            self.logger.log(msg)

    def find_session_for_obj(self, obj):
        for s in self.sessions:
            if s.contains(obj):
                return s
        return None

    def add_session(self, session):
        self.sessions.append(session)
        session.index = len(self.sessions)

    def add_lap(self, lap):
        self.laps.append(lap)

    def add_record(self, record):
        self.records.append(record)

    def _process(self):
        # Walk all records and wrap them in our types:
        for r in self.activity.records:
            rec = RecordWrapper.create(self, r)
            if rec is not None:
                rec.container = self

        # Collect all laps and records with the sessions they
        # belong with:
        for l in self.laps:
            s = self.find_session_for_obj(l)
            if s:
                s.add_lap(l)
        for r in self.records:
            s = self.find_session_for_obj(r)
            if s:
                s.add_record(r)

        # Create ST sessions and convert everything:
        for s in self.sessions:
            s.convert(self.user)

if __name__ == "__main__":
    class Logger(object):
        def log(self, msg):
            print >> sys.stderr, msg

    def printhelp():
        print "usage: python" + sys.argv[0] + " <uid> <password> <fit file>"

    def main():

        if len(sys.argv) != 4:
            printhelp()
            return 0

        uid = sys.argv[1]
        password = sys.argv[2]
        user = None
        with gripe.db.Tx.begin():
            u = grizzle.UserManager().get(uid)
            if u.authenticate(password = password):
                user = u
        if not user:
            print >> sys.stderr, "Authentication error"
            printhelp()
            return 0

        try:
            parser = FITParser(user, sys.argv[3])
            parser.setLogger(Logger())
            parser.parse()
            return 0
        except FitParseError, exception:
            sys.stderr.write(str(exception) + "\n")
            return 1

    sys.exit(main())

