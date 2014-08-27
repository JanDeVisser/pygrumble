#!/usr/bin/python

import sys
import traceback

import gripe
import gripe.conversions
import gripe.db
import grizzle
import grumble.geopt
import grumble.model
import sweattrails.device.exceptions
import sweattrails.device.fitparse
import sweattrails.config
import sweattrails.session

logger = gripe.get_logger(__name__)

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

    def log(self, msg, *args):
        if self.container is not None:
            self.container.log(msg, *args)

    def progress_init(self, msg, *args):
        if self.container is not None:
            self.container.progress_init(msg, *args)
    
    def progress(self, num):
        if self.container is not None:
            self.container.progress(num)
        
    def progress_end(self):
        if self.container is not None:
            self.container.progress_end()
        
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
        interval.interval_id = str(gripe.conversions.local_date_to_utc(self.start_time)) + "Z"
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
                gripe.conversions.semicircle_to_degrees(lat),
                gripe.conversions.semicircle_to_degrees(lon))
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
            self.start_time = self.get_data("start_time")
            
            q = sweattrails.session.Session.query()
            q.add_filter("start_time = ", self.start_time)
            q.add_filter("athlete = ", athlete)
            session = q.get()
            if session:
                raise sweattrails.device.exceptions.SessionExistsError(session)
                
            session = sweattrails.session.Session()
            session.athlete = athlete
            session.start_time = self.start_time
            session.inprogress = False
            profile = sweattrails.config.ActivityProfile.get_profile(athlete)
            assert profile, "fitparse.upload(): User %s has no profile" % athlete.uid()
            sessiontype = profile.get_default_SessionType(self.get_data("sport"))
            assert sessiontype, "fitparse.upload(): User %s has no default session type for sport %s" % (athlete.uid(), self.get_data("sport"))
            session.sessiontype = sessiontype
            self.log("Converting session {}/{}", self.index, len(self.container.sessions))
            self.convert_interval(session)

            num = len(self.laps)
            if num > 1:
                self.progress_init("Session {}/{}: Converting {} intervals", self.index, len(self.container.sessions), num)
                for ix in range(num):
                    lap = self.laps[ix]
                    self.progress(int((float(ix) / float(num)) * 100.0))
                    interval = sweattrails.session.Interval(parent = session)
                    lap.convert_interval(interval)
                self.progress_end()

            num = len(self.records)                
            self.progress_init("Session {}/{}: Converting {} waypoints", self.index, len(self.container.sessions), num)
            for ix in range(num):
                record = self.records[ix]
                self.progress(int((float(ix) / float(num)) * 100.0))
                record.convert(session)
            self.progress_end()
                                
            self.progress_init("Analyzing session {}/{}", self.index, len(self.container.sessions))
            def callback(percentage):
                self.progress(percentage)
            session.analyze(callback)
            self.progress_end()
            return session

class FITParser(object):
    def __init__(self, user, filename, logger = None):
        self.user = user
        self.filename = filename
        self.activity = None
        self.sessions = []
        self.laps = []
        self.records = []
        self.logger = logger

    def parse(self):
        try:
            self.log("Reading FIT file {}", self.filename)
            self.activity = sweattrails.device.fitparse.Activity(self.filename)
            self.log("Parsing FIT file {}", self.filename)
            self.activity.parse()
            self.log("Processing FIT file {}", self.filename)
            self._process()
            self.log("FIT file {} converted", self.filename)
            return None
        except sweattrails.device.fitparse.FitParseError as exception:
            raise sweattrails.device.exceptions.FileImportError(exception)

    def log(self, msg, *args):
        if self.logger is not None:
            self.logger.log(msg, *args)

    def progress_init(self, msg, *args):
        if self.logger is not None:
            self.logger.progress_init(msg, *args)
    
    def progress(self, num):
        if self.logger is not None:
            self.logger.progress(num)
        
    def progress_end(self):
        if self.logger is not None:
            self.logger.progress_end()
        
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
        def log(self, msg, *args):
            print >> sys.stderr, msg.format(args)
            
        def progress_init(self, msg, *args):
            self.curr_progress = 0
            sys.stdout.write((msg + " [").format(*args))
            sys.stdout.flush()
            
        def progress(self, new_progress):
            diff = int((new_progress - self.curr_progress) / 10.0) 
            sys.stderr.write("." * diff)
            sys.stdout.flush()
            self.curr_progress = new_progress
            
        def progress_end(self):
            sys.stdout.write("]\n")
            sys.stdout.flush()
            

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
            parser = FITParser(user, sys.argv[3], Logger())
            parser.parse()
            return 0
        except:
            traceback.print_exc()
            return 1

    sys.exit(main())

