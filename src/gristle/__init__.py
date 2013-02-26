__author__="jan"
__date__ ="$24-Feb-2013 11:13:48 AM$"

import webapp2

import grumble
import grit
from grit import handlers
from Model import Grumble

class ManageUsers(handlers.PageHandler):
    def get_template(self):
        return "user" if self.key() else "users"

    def get(self, key = None):
        return super(ManageUsers, self).get(key, "user")

app = webapp2.WSGIApplication( [
        webapp2.Route(r'/users', handler=ManageUsers, name='manage-users'),
        webapp2.Route(r'/users/<key>', handler=ManageUsers, name='manage-user'),
    ], debug=True)

