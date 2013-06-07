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

logger = gripe.get_logger("grizzle")

class UserGroup(grumble.Model, grit.auth.AbstractUserGroup):
    _flat = True
    group = grumble.TextProperty(is_key = True, is_label = True)
    has_roles = grumble.ListProperty()

    def gid(self):
        return self.group

    def _explicit_roles(self):
        return set(self.has_roles)

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

    def _explicit_roles(self):
        return set(self.has_roles)

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

    def add(self, userid, password):
        user = self.get(userid)
        if user:
            raise grit.auth.UserExists(userid)
        else:
            user = User(email = userid, password = password, confirmation_code = self.confirmation_code())
            user.put()
            return user.confirmation_code

    def confirm(self, userid, code):
        user = User.query("email = ", userid, "confirmation_code = ", code, ancestor = None).fetch()
        if user:
            user.confirmation_code = None
            user.put()
        else:
            raise grit.auth.InvalidConfirmationCode()

def currentuser():
    return UserManager().get(grumble.get_sessionbridge().userid())

class ManageUsers(grit.handlers.PageHandler):
    def get_template(self):
        return "user" if self.key() else "users"

    def get(self, key = None, kind = "user"):
        try:
            return super(ManageUsers, self).get(key = key, kind = "user")
        except:
            logger.exception("exception in get()")

class JSONUser(grit.handlers.JSONHandler):
    def _set_password(self, user):
        um = grit.Session.get().get_usermanager()
        newpasswd = um.gen_password()
        user.password = newpasswd
        user.confirmation_code = None
        user.put()
        msg = gripe.smtp.TemplateMailMessage("adminpasswordreset")
        return msg.send(user.email, "Password Reset", {"password": newpasswd})

    def create_user(self, descriptor):
        user = User.create(descriptor)
        return self._set_password(user)

    def generate_new_password(self, userid):
        um = grit.Session.get().get_usermanager()
        user = um.get(userid)
        return self._set_password(user) if user else None

    def request_password_reset(self, userid):
        um = grit.Session.get().get_usermanager()
        user = um.get(userid)
        if user:
            code = um.confirmation_code()
            user.confirmation_code = code
            user.put()
            msg = gripe.smtp.TemplateMailMessage("passwordreset")
            return msg.send(user.email, "Password Reset", {"confirmation_code": code})
        else:
            return None

    def confirm_password_reset(self, userid, code, newpasswd):
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


app = webapp2.WSGIApplication([
        webapp2.Route(r'/users', handler = ManageUsers, name = 'manage-users', defaults = { "kind": "user" }),
        webapp2.Route(r'/users/<key>', handler = ManageUsers, name = 'manage-user', defaults = { "kind": "user" }),
        webapp2.Route(r'/user/<key>/json', handler = JSONUser, name = 'manage-user-json', defaults = { "kind": "user" }),
    ], debug = True)
