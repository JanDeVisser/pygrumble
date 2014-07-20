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


class RecordWrapper(object):
    def __init__(self, rec):
        self._data = rec.as_dict(True)
        self._fitrec = rec
        self._grumble_obj = None
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
        interval.interval_id = local_date_to_utc(self.get_data("start_time")) + "Z"
        interval.distance = self.get_data("total_distance")
        interval.start_time = self.get_data("start_time")
        interval.elapsed_time = self.get_data("total_elapsed_time")
        interval.duration = self.get_data("total_timer_time")
        interval.calories_burnt = self.get_data("total_calories")
        interval.put()
        return interval

class FITRecord(RecordWrapper):
    def convert(self, session):
        wp = sweattrails.session.Waypoint(parent = session)
        wp.timestamp = self.get_data("timestamp")
        lat = self.get_data("position_lat")
        lon = self.get_data("position_lon")
        if lat and lon:
            wp.location = grumble.geopt.GeoPt(lat, lon)
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
        self.start = self.data["start_time"]
        self.end = self.data["timestamp"]
        self.laps = []
        self.records = []

    def contains(self, obj):
        return self.start < obj.data["timestamp"] <= self.end

    def add_lap(self, lap):
        self.laps.append(lap)

    def add_record(self, record):
        self.records.append(record)

    def convert(self, athlete):
        assert athlete, "fitparse.upload(): athlete is None"
        session = sweattrails.session.Session()
        session.athlete = athlete
        session.inprogress = False
        profile = sweattrails.config.ActivityProfile.get_profile(athlete)
        assert profile, "fitparse.upload(): User %s has no profile" % athlete.uid()
        sessiontype = profile.get_default_SessionType(self.get_data("sport"))
        assert sessiontype, "fitparse.upload(): User %s has no default session type for sport %s" % (athlete.uid(), self.get_data("sport"))
        session.sessiontype = sessiontype
        self.upload_interval(session)
        for lap in self.laps:
            interval = sweattrails.session.Interval(parent = session)
            lap.convert_interval(interval)
        for record in self.records:
            record.convert(session)
        session.analyze()
        return session

class ActivityWrapper(object):
    def __init__(self, activity):
        self.activity = activity
        self.sessions = []
        self.laps = []
        self.records = []

    def find_session_for_obj(self, obj):
        for s in self.sessions:
            if s.contains(obj):
                return s
        return None

    def add_session(self, session):
        self.sessions.append(session)

    def add_lap(self, lap):
        self.laps.append(lap)

    def add_record(self, record):
        self.records.append(record)

    def process(self, user):
        # Walk all records and wrap them in our types:
        for r in self.activity.records:
            RecordWrapper.create(self, r)

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
            s.convert(user)

def convert(user, filename):
    activity = Activity(filename)
    activity.parse()
    wrapper = ActivityWrapper(activity)
    wrapper.process(user)
    return None

if __name__ == "__main__":

    def printhelp():
        print "usage: python" + sys.argv[0] + "<uid> <password> <fit file>"

    def main():

        if len(sys.argv) != 1:
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
            convert(user, sys.argv[3])
            return 0
        except FitParseError, exception:
            sys.stderr.write(str(exception) + "\n")
            return 1

    sys.exit(main())

