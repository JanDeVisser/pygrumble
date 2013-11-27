# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Oct-2013 8:34:23 AM$"

import grizzle
import grumble
import grumble.geopt

class UserProfile(grizzle.UserPart):
    country = grumble.StringProperty(default = "CA")
    dob = grumble.DateProperty()
    gender = grumble.StringProperty(choices = set(['male', 'female', 'other']), default = 'other')
    height = grumble.IntegerProperty(default = 170)	# in cm
    units = grumble.StringProperty(choices = set(['metric', 'imperial']), default = 'metric')
    location = grumble.geopt.GeoPtProperty()
    whoami = grumble.StringProperty(multiline=True)
    regkey = grumble.StringProperty()
    uploads = grumble.IntegerProperty(default = 0)
    last_upload = grumble.DateTimeProperty()

class WeightMgmt(grizzle.UserPart):
    pass


class BMIProperty(grumble.FloatProperty):
    transient = True
    def getvalue(self, instance):
        user = instance.parent().get().parent()
        profile = user().get_part(UserProfile)
        h_m = float(profile.height) / 100
        return instance.weight / (h_m * h_m)
    
    def setvalue(self, instance, value):
        pass

class History(grumble.Model):
    snapshotdate = grumble.DateProperty(auto_now_add=True)
    weight = grumble.FloatProperty(default = 0.0)		# in kg
    bmi = BMIProperty()
    bfPercentage = grumble.FloatProperty(default = 0.0)
    waist = grumble.FloatProperty(default = 0.0)		# in cm
    bpHigh = grumble.IntegerProperty(default = 120)
    bpLow = grumble.IntegerProperty(default = 80)
    temperature = grumble.FloatProperty(default = 37.0)
    sleep = grumble.FloatProperty(default = 0.0)
    health = grumble.StringProperty(default = '')
    
class SeizureMgmt(grizzle.UserPart):
    markers = grumble.ListProperty(verbose_name = "Markers")
    triggers = grumble.ListProperty(verbose_name = "Triggers")

class SeizureLog(grumble.Model):
    timestamp = grumble.DateTimeProperty(auto_now_add=True)
    description = grumble.TextProperty()
    severity = grumble.IntProperty()
    markers = grumble.JSONProperty()
    triggers = grumble.JSONProperty()

