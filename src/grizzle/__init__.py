__author__ = "jan"
__date__ = "$24-Feb-2013 11:13:48 AM$"

import webapp2

import gripe
import gripe.smtp
import grumble
import grit
import grit.auth
import grit.handlers
import grit.role

logger = gripe.get_logger(__name__)

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
    confirmation_code = grumble.TextProperty()
    display_name = grumble.TextProperty(is_label = True)
    has_roles = grumble.ListProperty()

    def uid(self):
        return self.email

    def groups(self):
        return { gfu.group for gfu in self.groupsforuser_set }

    def generate_new_password(self):
        newpasswd = grit.auth.AbstractUserManager.gen_password()
        self.password = newpasswd
        self.put()
        msg = gripe.smtp.TemplateMailMessage("adminpasswordreset")
        return msg.send(self.email, "Password Reset", {"password": newpasswd})

class GroupsForUser(grumble.Model):
    _flat = True
    user = grumble.ReferenceProperty(reference_class = User)
    group = grumble.ReferenceProperty(reference_class = UserGroup)

class UserManager(grit.auth.AbstractUserManager):
    def get(self, userid):
        return User.get_by_key(userid)

    def login(self, userid, password):
        pwdhash = grumble.PasswordProperty.hash(password)
        user = User.query("email = ", userid, "password = ", pwdhash, ancestor = None).fetch()
        if user:
            assert isinstance(user, User), "Huh? More than one user with the same email and password?? %s" % type(user)
        if user and user.confirmation_code:
            user = None
        return user

    def request_pwd_reset(self, userid):
        user = self.get(userid)
        if user:
            code = self._confirmation_code()
            user.confirmation_code = code
            user.put()
            return code
        else:
            return None

    def confirm_pwd_reset(self, userid, code, newpasswd):
        if userid and code:
            user = User.query("email = ", userid, "confirmation_code = ", code, ancestor = None).fetch()
            if user:
                assert isinstance(user, User), "Huh? More than one user with the same email and confirmation_code?? %s" % type(user)
            if not user:
                return False
            else:
                user.password = newpasswd
                user.confirmation_code = None
                user.put()
                return True
        else:
            return False


class ManageUsers(grit.handlers.PageHandler):
    def get_template(self):
        return "user" if self.key() else "users"

    def get(self, userid = None):
        return super(ManageUsers, self).get(userid, "user")


app = webapp2.WSGIApplication([
        webapp2.Route(r'/users', handler = ManageUsers, name = 'manage-users'),
        webapp2.Route(r'/users/<userid>', handler = ManageUsers, name = 'manage-user'),
    ], debug = True)













