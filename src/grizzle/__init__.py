__author__ = "jan"
__date__ = "$24-Feb-2013 11:13:48 AM$"

import webapp2

import gripe
import gripe.smtp
import grumble
import gripe.auth
import grit.handlers
import gripe.role

logger = gripe.get_logger("grizzle")

class UserGroup(grumble.Model, gripe.auth.AbstractUserGroup):
    _flat = True
    group = grumble.TextProperty(is_key = True, is_label = True)
    has_roles = grumble.ListProperty()

    def gid(self):
        return self.group

    def _explicit_roles(self):
        return set(self.has_roles)

UserStatus = gripe.Enum(['Unconfirmed', 'Active', 'Admin', 'Banned', 'Inactive', 'Deleted'])
GodList = ('jan@de-visser.net',)

class User(grumble.Model, gripe.auth.AbstractUser):
    _flat = True
    email = grumble.TextProperty(is_key = True)
    password = grumble.PasswordProperty()
    status = grumble.TextProperty(choices = UserStatus, default = 'Unconfirmed')
    display_name = grumble.TextProperty(is_label = True)
    has_roles = grumble.ListProperty()

    def is_active(self):
        """
          An active user is a user currently in good standing.
        """
        return self.status == 'Active'

    def is_admin(self):
        return ("admin" in self.has_roles and self.is_active()) or (self.status == 'Admin') or self.is_god()

    def is_god(self):
        return self.uid() in GodList

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

class UserManager(gripe.auth.AbstractUserManager):
    def get(self, userid):
        return User.get_by_key(userid)

    def login(self, userid, password):
        logger.debug("UserManager.login(%s, %s)", userid, password)
        pwdhash = grumble.PasswordProperty.hash(password)
        user = User.query("email = ", userid, "password = ", pwdhash, ancestor = None).fetch()
        if user:
            assert isinstance(user, User), "Huh? More than one user with the same email and password?? %s" % type(user)
        if user is None:
            logger.debug("UserManager.login(%s, %s) Login failed", userid, password)            
        if user and not user.is_active():
            logger.debug("UserManager.login(%s, %s) User not active", userid, password)
            user = None
        return user

    def add(self, userid, password):
        logger.debug("UserManager.add(%s, %s)", userid, password)
        user = self.get(userid)
        if user and user.exists():
            logger.debug("UserManager.add(%s, %s) User exists", userid, password)
            raise gripe.auth.UserExists(userid)
        else:
            user = User(email = userid, password = password)
            user.put()
            logger.debug("UserManager.add(%s, %s) OK", userid, password)
            return user.id()

    def confirm(self, userid, status = 'Active'):
        logger.debug("UserManager.confirm(%s, %s)", userid, status)
        user = self.get(userid)
        if user and user.exists():
            logger.debug("UserManager.confirm(%s, %s) OK", userid, status)
            user.status = status
            if 'user' not in user.has_roles:
                user.has_roles.append('user')
            user.put()
        else:
            logger.debug("UserManager.confirm(%s, %s) doesn't exists", userid, status)
            raise gripe.auth.UserDoesntExists(userid)
        
    def changepwd(self, userid, oldpassword, newpassword):
        logger.debug("UserManager.changepwd(%s, %s, %s)", userid, oldpassword, newpassword)
        user = self.login(userid, oldpassword)
        if user:
            logger.debug("UserManager.changepwd(%s, %s, %s) login OK. Changing pwd", userid, oldpassword, newpassword)
            user.password = newpassword
            user.put()
        else:
            raise gripe.auth.BadPassword(userid)

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
