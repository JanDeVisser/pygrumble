# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Oct-2013 8:34:23 AM$"

import grumble
import grumble.geopt

class UserProfile(grizzle.UserComponent):
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

