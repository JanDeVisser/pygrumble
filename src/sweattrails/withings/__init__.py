__author__ = "jan"
__date__ = "$12-Sep-2015 2:10:37 PM$"

import datetime
import httplib
import json

import gripe
import gripe.db
import grumble.model
import grumble.property
import sweattrails.qt.imports
import sweattrails.userprofile

logger = gripe.get_logger(__name__)

withings_user_id = "2497930"
withings_public_key = "82435cd4a1ca8d8b"
withings_host = "wbsapi.withings.net"
withings_url = "/measure?action=getmeas&userid=%s&publickey=%s&category=1" % (withings_user_id, withings_public_key)

class WithingsMeasurement(grumble.model.Model):
    timestamp = grumble.property.DateTimeProperty()
    type = grumble.property.IntegerProperty()
    value = grumble.property.FloatProperty()
    
    def convert(self):
        part = self.parent()
        if self.type in [1, 6]:
            h = sweattrails.userprofile.WeightHistory.query("snapshotdate = ", self.timestamp, parent = part)
            if not h:
                h = sweattrails.userprofile.WeightHistory(snapshotdate = self.timestamp, parent = part)
            if self.type == 1:
                h.weight = self.value
            else:
                h.bfPercentage = self.value
            h.put()
        elif self.type in [9, 10, 11]:
            h = sweattrails.userprofile.CardioVascularHistory.query("snapshotdate = ", self.timestamp, parent = part)
            if not h:
                h = sweattrails.userprofile.CardioVascularHistory(snapshotdate = self.timestamp, parent = part)
            if self.type == 9:
                h.bpLow = self.value
            elif self.type == 10:
                h.bpHigh = self.value
            else:
                h.resting_hr = self.value
            h.put()

class WithingsJob(sweattrails.qt.imports.Job):
    def __init__(self):
        super(WithingsJob, self).__init__()

    def handle(self):
        self.started("Downloading Withings data")
        conn = httplib.HTTPConnection(withings_host)
        conn.request("GET", withings_url)
        response = conn.getresponse()
        if response.status == 200:
            if self._parse_results(user, response):
                self.finished("Withings data downloaded")
        else:
            logger.error("Error downloading Withings data: %s", response.status)
            self.error("downloading Withing data", response.status)
        
    def _parse_results(self, user, response):
        results = json.load(response)
        if results["status"] != 0:
            self.error("downloading Withing data. Withings reports error",
                       results["status"])
            return False
        part = user.get_part("WeightMgmt")
        if not part:
            self.error("downloading Withings data", "No WeightMgmt part found.")
            return False
        
        with gripe.db.Tx.begin():
            for measuregrp in results["body"]["measuregrps"]:
                ts = datetime.datetime.fromtimestamp(measuregrp["date"])
                wms = WithingsMeasurement.query("timestamp = ", ts, parent = part)
                if not wms:
                    for measure in measuregrp["measures"]:
                        self._convert_measure(part, ts, measure)
        return True
    
    def _convert_measure(self, part, ts, measure):
        wm = WithingsMeasurement(parent = part, timestamp = ts)
        wm.type = measure["type"]
        wm.value = measure["value"] * pow(10, measure["unit"])
        wm.put()
        wm.convert()
                        
    @classmethod
    def get_thread(cls):
        if not cls._singleton:
            cls._singleton = WithingsThread()
        return cls._singleton
    
