__author__ = "jan"
__date__ = "$24-Feb-2013 11:13:48 AM$"

import sys
import webapp2

import gripe
import gripe.smtp
import grumble
import gripe.auth
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

class UserComponent(grumble.Model):
    pass

"""
    Banned - User is still there, content is still there, user cannot log in.
        Revertable.
    Inactive - At user's request, User is "deleted", content deleted, user 
        cannot log in. Not revertable.
    Deleted - Admin "deleted" user, content deleted, user cannot log in. 
        Not revertable.
"""
UserStatus = gripe.Enum(['Unconfirmed', 'Active', 'Admin', 'Banned', 'Inactive', 'Deleted'])
GodList = ('jan@de-visser.net',)

class User(grumble.Model, gripe.auth.AbstractUser):
    _flat = True
    _resolved_parts = set()
    email = grumble.TextProperty(is_key = True)
    password = grumble.PasswordProperty()
    status = grumble.TextProperty(choices = UserStatus, default = 'Unconfirmed')
    display_name = grumble.TextProperty(is_label = True)
    has_roles = grumble.ListProperty()
    
    def after_store(self):
        for m in gripe.Config.app.grizzle.userparts:
            if m not in self._resolved_parts:
                logger.debug("grizzle.User.after_store(%s): Resolving user part %s", self.email, m)
                gripe.resolve(m)
                self._resolved_parts.add(m)
            logger.debug("grizzle.User.after_store(%s): Creating user part %s", self.email, m)
            k = grumble.Model.for_name(m)
            component = k(parent = self)
            component.put()
            
    def sub_to_dict(self, d, **flags):
        if flags.get("include_components"):
            for component in grumble.Query(UserComponent, False, True).set_parent(self):
                (_, _, k) = component.kind().rpartition(".")
                d[k] = component.to_dict()
        return d

    def on_update(self, d, **flags):
        for component in grumble.Query(UserComponent, False, True).set_parent(self):
            (_, _, k) = component.kind().rpartition(".")
            if k in d:
                comp = d[k]
                component.update(comp, **flags)

#    def is_root(self):
#        return self.email == Config.app.grizzle.root
#    
#    @classmethod
#    def get_root(cls):
#        return cls.by("email", Config.app.grizzle.root)

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

    def add(self, userid, password, display_name = None):
        logger.debug("UserManager.add(%s, %s)", userid, password)
        user = self.get(userid)
        if user and user.exists():
            logger.debug("UserManager.add(%s, %s) User exists", userid, password)
            raise gripe.auth.UserExists(userid)
        else:
            user = User(email = userid, password = password, display_name = display_name)
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

app = webapp2.WSGIApplication([
        webapp2.Route(
            r'/users/<key>',
            handler = "grit.handlers.PageHandler", name = 'manage-user',
            defaults = {
                "kind": User
            }
        ),
        webapp2.Route(
            r'/users',
            handler = "grit.handlers.PageHandler", name = 'manage-users',
            defaults = {
                "kind": User
            }
        ) # ,
        # webapp2.Route(r'/user/<key>/json', handler = JSONUser, name = 'manage-user-json', defaults = { "kind": "user" }),
    ], debug = True)
