import webapp2

__author__="jan"
__date__ ="$15-Sep-2013 10:58:20 AM$"

app = webapp2.WSGIApplication([
        webapp2.Route(
            r'/profile',
            handler = "grit.handlers.PageHandler", name = 'user-profile',
            defaults = {
                "kind": "grizzle.user",
                "key": '__userobjid',
                "template": "/sweattrails/profile/view"
            }
        ),
        webapp2.Route(
            r'/weight',
            handler = "grit.handlers.PageHandler", name = 'weight-mgmt',
            defaults = {
                "kind": "grizzle.user",
                "key": '__userobjid',
                "template": "/sweattrails/weightmgmt/view"
            }
        ),
    ], debug = True)
