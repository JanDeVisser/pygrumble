# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Oct-2013 8:34:23 AM$"

import grizzle
import grumble
import grumble.property
import grumble.geopt


class UserProfile(grizzle.UserPart):
    country = grumble.StringProperty(default = "CA")
    dob = grumble.DateProperty()
    gender = grumble.StringProperty(choices = ['male', 'female', 'other'], default = 'other')
    height = grumble.IntegerProperty(default = 170)  # in cm
    units = grumble.StringProperty(choices = ['metric', 'imperial'], default = 'metric')
    location = grumble.geopt.GeoPtProperty()
    whoami = grumble.StringProperty(multiline = True)
    regkey = grumble.StringProperty()
    uploads = grumble.IntegerProperty(default = 0)
    last_upload = grumble.DateTimeProperty()

    def after_insert(self):
        pass

class BikeProfile(grizzle.UserPart):
    def get_ftp(self, on_date = None):
        ftp = 0
        q = FTPHistory.query(parent = self).add_sort("snapshotdate")
        if on_date:
            q.add_filter("snapshotdate <= ", on_date)
        hentry = q.get()
        if hentry:
            ftp = hentry.ftp
        return ftp

    def set_ftp(self, ftp, on_date = None):
        hentry = FTPHistory(parent = self)
        hentry.ftp = ftp
        if on_date:
            hentry.snapshotdate = on_date
        hentry.put()

    def get_max_power(self, on_date = None):
        max_power = 0
        q = MaxPowerHistory.query(parent = self).add_sort("snapshotdate")
        if on_date:
            q.add_filter("snapshotdate <= ", on_date)
        hentry = q.get()
        if hentry:
            max_power = hentry.max_power
        return max_power

    def set_max_power(self, max_power, on_date = None):
        current = self.get_max_power(on_date)
        if current < max_power:
            hentry = MaxPowerHistory(parent = self)
            hentry.max_power = max_power
            if on_date:
                hentry.snapshotdate = on_date
            hentry.put()

    def get_watts_per_kg(self, watts, on_date):
        ret = 0
        weightpart = WeightMgmt.get_userpart(self.get_user())
        if weightpart is not None:
            weight = weightpart.get_weight(on_date)
            ret = watts/weight
        return ret


class FTPHistory(grumble.Model):
    snapshotdate = grumble.property.DateProperty(auto_now_add = True)
    ftp = grumble.property.IntegerProperty(default = 0)  # FTP in Watts


class MaxPowerHistory(grumble.Model):
    snapshotdate = grumble.property.DateProperty(auto_now_add = True)
    max_power = grumble.property.IntegerProperty(default = 0)  # Max power in Watts


class RunProfile(grizzle.UserPart):
    pass


class WeightMgmt(grizzle.UserPart):
    def get_weight(self, on_date = None):
        weight = 0
        q = WeightHistory.query(parent = self).add_sort("snapshotdate")
        if on_date:
            q.add_filter("snapshotdate <= ", on_date)
        hentry = q.get()
        if hentry:
            weight = hentry.weight
        return weight


class BMIProperty(grumble.FloatProperty):
    transient = True
    def getvalue(self, instance):
        user = instance.parent().get().parent()
        profile = user().get_part(UserProfile)
        h_m = float(profile.height) / 100
        return instance.weight / (h_m * h_m)

    def setvalue(self, instance, value):
        pass

class WeightHistory(grumble.Model):
    snapshotdate = grumble.DateProperty(auto_now_add = True)
    weight = grumble.FloatProperty(default = 0.0)  # in kg
    bmi = BMIProperty()
    bfPercentage = grumble.FloatProperty(default = 0.0)
    waist = grumble.FloatProperty(default = 0.0)  # in cm

class CardioVascularHistory(grumble.Model):
    snapshotdate = grumble.DateProperty(auto_now_add = True)
    bpHigh = grumble.IntegerProperty(default = 120, verbose_name = "Systolic (high) Blood Pressure")
    bpLow = grumble.IntegerProperty(default = 80, verbose_name = "Diastolic (low) Blood Pressure")
    resting_hr = grumble.IntegerProperty(default = 60, verbose_name = "Resting Heartrate")

class WellnessDiary(grumble.Model):
    snapshotdate = grumble.DateProperty(auto_now_add = True)
    mood = grumble.IntegerProperty(minvalue = 1, maxvalue = 10)
    sleep_time = grumble.FloatProperty(default = 0.0, verbose_name = "Sleep Time")
    sleep_q = grumble.IntegerProperty(minvalue = 1, maxvalue = 10, verbose_name = "Sleep Quality")
    health = grumble.TextProperty(multiline = True, verbose_name = "Health Notes")

class SeizureMgmt(grizzle.UserPart):
    markers = grumble.ListProperty(verbose_name = "Markers")
    triggers = grumble.ListProperty(verbose_name = "Triggers")

class SeizureLog(grumble.Model):
    timestamp = grumble.DateTimeProperty(auto_now_add = True)
    description = grumble.TextProperty()
    severity = grumble.IntProperty()
    markers = grumble.JSONProperty()
    triggers = grumble.JSONProperty()

