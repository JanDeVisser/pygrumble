import webapp2
import grizzle
import grumble
import grumble.geopt

__author__="jan"
__date__ ="$15-Sep-2013 10:58:20 AM$"

def get_flag(country):
    return "http://flagspot.net/images/{0}/{1}.gif".format(country.code[0:1].lower(), country.code.lower())

class Country(grumble.Model):
    name = grumble.StringProperty(verbose_name = "Country name", is_label = True)
    code = grumble.StringProperty(verbose_name = "ISO 3166-1 code", is_key = True)
    flag_url = grumble.StringProperty(transient = True, getter = get_flag)

class Profile(grizzle.UserComponent):
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

app = webapp2.WSGIApplication([
        webapp2.Route(
            r'/profile',
            handler = "grit.handlers.PageHandler", name = 'user-profile',
            defaults = {
                "kind": "grizzle.user",
                "key": '__userobjid',
                "template": "/sweattrails/profile/view"
            }
        )
    ], debug = True)
