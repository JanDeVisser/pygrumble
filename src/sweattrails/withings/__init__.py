__author__ = "jan"
__date__ = "$12-Sep-2015 2:10:37 PM$"

import datetime
import json
import urllib2

import gripe
import grumble.model
import grumble.property
import sweattrails.userprofile

logger = gripe.get_logger(__name__)

withings_user_id = "2497930"
withings_public_key = "82435cd4a1ca8d8b"
withings_host = "http://wbsapi.withings.net"
withings_url = withings_host + "/measure?action=getmeas&userid=%s&publickey=%s&category=1"

class WithingsMeasurement(grumble.model.Model):
    timestamp = grumble.property.DateTimeProperty()
    type = grumble.property.IntegerProperty()
    value = grumble.property.FloatProperty()
    
    def convert(self):
        if self.type in [1, 6]:
            h = sweattrails.userprofile.WeightHistory.query("snapshotdate = ", self.timestamp, parent = part)
            if not h:
                h = sweattrails.userprofile.WeightHistory(snapshotdate = self.timestamp, parent = part)
            if h == 1:
                h.weight = self.value
            else:
                h.bfPercentage = self.value
            h.put()
        elif self.type in [9, 10, 11]:
            h = sweattrails.userprofile.CardioVascularHistory.query("snapshotdate = ", self.timestamp, parent = part)
            if not h:
                h = sweattrails.userprofile.CardioVascularHistory(snapshotdate = self.timestamp, parent = part)
            if h == 9:
                h.bpLow = self.value
            elif h == 10:
                h.bpHigh = self.value
            else:
                h.resting_hr = self.value
            h.put()

class WithingsDownloader(object):
    def download(self, user):
        url = withings_url % (withings_user_id, withings_public_key)
        response = urllib2.open(url)
        if response.getcode() == 200:
            return self._parse_results(user, response)
        else:
            logger.error("Error downloading Withings data: %s", response.getcode())
            return False
        
    def _parse_results(self, user, response):
        results = json.load(response)
        if results["status"] != 0:
            logger.error("Withings reports error: %s", results["status"])
            return False
        part = user.get_part("WeightMgmt")
        for measuregrp in results["body"]["measuregrps"]:
            ts = datetime.datetime.fromtimestamp(measuregrp["date"])
            wms = WithingsMeasurement.query("timestamp = ", ts, parent = part)
            if not wms:
                for measure in measuregrp["measures"]:
                    self._convert_measure(part, measure)
        return True
    
    def _convert_measure(self, part, measure):
        wm = WithingsMeasurement(parent = part, timestamp = ts)
        wm.type = measure["type"]
        wm.value = measure["value"] * pow(10, measure["unit"])
        wm.put()
        wm.convert()
        
                    
