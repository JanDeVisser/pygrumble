__author__="jan"
__date__ ="$24-Feb-2013 11:13:48 AM$"

import webapp2

import grumble
import grit
import grit.auth
import grit.handlers
import grit.role

class UserGroup(grumble.Model, grit.auth.AbstractUserGroup):
    _flat = True
    group = grumble.TextProperty(is_key = True, is_label = True)
    has_roles = grumble.ListProperty()

    def gid(self):
        return self.group

class User(grumble.Model, grit.auth.AbstractUser):
    _flat = True
    email = grumble.TextProperty(is_key = True)
    password = grumble.PasswordProperty()
    display_name = grumble.TextProperty(is_label = True)
    has_roles = grumble.ListProperty()

    def uid(self):
        return self.email

    def groups(self):
        return { gfu.group for gfu in self.groupsforuser_set }

    @classmethod
    def login(cls, email, password):
        hash = grumble.PasswordProperty.hash(password)
        user = User.query("email = ", email, "password = ", hash, ancestor = None).fetch()
        if user:
            assert isinstance(user, User), "Huh? More than one user with the same email and password?? %s" % type(user)
        return user

class GroupsForUser(grumble.Model):
    _flat = True
    user = grumble.ReferenceProperty(reference_class = User)
    group = grumble.ReferenceProperty(reference_class = UserGroup)

class UserManager(grit.auth.AbstractUserManager):
    def get(self, userid):
        return User.get(userid)

    def login(self, userid, password):
        return User.login(userid, password)

class ManageUsers(grit.handlers.PageHandler):
    def get_template(self):
        return "user" if self.key() else "users"

    def get(self, key = None):
        return super(ManageUsers, self).get(key, "user")

app = webapp2.WSGIApplication( [
        webapp2.Route(r'/users', handler=ManageUsers, name='manage-users'),
        webapp2.Route(r'/users/<key>', handler=ManageUsers, name='manage-user'),
    ], debug=True)

