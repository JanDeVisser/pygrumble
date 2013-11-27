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

@grumble.abstract
class UserPart(grumble.Model):

    @classmethod
    def get_userpart(cls, user):
        return user.get_part(cls)
    
    def urls(self):
        return self._urls if hasattr(self, "_urls") else None

class UserPartKennel(UserPart):
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

class UserPartToggle(grumble.BooleanProperty):
    transient = True
    def __init__(self, partname, *args, **kwargs):
        super(UserPartToggle, self).__init__(*args, **kwargs)
        self.partname = partname
        
    def _init_parts(self, instance):
        if not hasattr(instance, "_parts"):
            instance._parts = { grumble.Model.for_name(pn).basekind().lower(): None for pn in gripe.Config.app.grizzle.userparts }
    
    def setvalue(self, instance, value):
        self._init_parts(instance)
        if (instance._parts[self.name] is not None) and not(value):
            p = instance._parts[self.name]
            instance._parts[self.name] = None
            for kennel in grumble.Query(UserPartKennel, keys_only = True, include_subclasses = True).set_parent(instance):
                p.set_parent(kennel)
                p.put()
        elif (instance._parts[self.name.lower()] is None) and value and not hasattr(instance, "_brandnew"):
            p = None
            for kennel in grumble.Query(UserPartKennel, keys_only = True, include_subclasses = True).set_parent(instance):
                for p in grumble.Query(grumble.Model.for_name(self.partname), keys_only = True, include_subclasses = True).set_parent(kennel):
                    p.set_parent(instance)
                    p.put()
            if p is None:
                p = grumble.Model.for_name(self.partname)(parent = instance)
                p.put()
            instance._parts[self.name.lower()] = p
        
    def getvalue(self, instance):
        self._init_parts(instance)
        return instance._parts[self.name] is not None

def customize_user_class(cls):
    for (partname, partdef) in gripe.Config.app.grizzle.userparts.items():
        (_, _, name) = partname.rpartition(".")
        name = name.lower()
        partcls = gripe.resolve(partname)
        if "urls" in partdef and partdef.urls:
            partcls._urls = gripe.url.UrlCollection(name, partdef.label, 9, partdef.urls)
        if partdef.configurable:
            propdef = UserPartToggle(name, verbose_name = partdef.label, 
                default = partdef.default)
            cls.add_property(name, propdef)

class User(grumble.Model, gripe.auth.AbstractUser):
    _flat = True
    _customizer = staticmethod(customize_user_class)
    email = grumble.TextProperty(is_key = True)
    password = grumble.PasswordProperty()
    status = grumble.TextProperty(choices = UserStatus, default = 'Unconfirmed')
    display_name = grumble.TextProperty(is_label = True)
    has_roles = grumble.ListProperty()
    
    def after_insert(self):
        kennel = UserPartKennel(parent = self)
        kennel.put()
        for (partname, partdef) in gripe.Config.app.grizzle.userparts.items():
            if partdef.default:
                part = grumble.Model.for_name(partname)(parent = self)
                part.put()
            
    def sub_to_dict(self, d, **flags):
        if "include_parts" in flags:
            for (k, part) in self._parts.items():
                if part:
                    d[k] = part.to_dict(**flags)
        return d

    def on_update(self, d, **flags):
        for (k, part) in self._parts.items():
            if (k in d) and part:
                p = d[k]
                part.update(p, **flags)

    def get_part(self, part):
        self._load()
        k = part if (isinstance(part, basestring)) else part.basekind().lower()
        return self._parts[k] if k in self._parts else None
    
    def after_load(self):
        self._parts = { grumble.Model.for_name(pn).basekind().lower(): None for pn in gripe.Config.app.grizzle.userparts }
        for part in grumble.Query(UserPart, keys_only = False, include_subclasses = True).set_parent(self):
            k = part.basekind().lower()            
            self._parts[k] = part
            setattr(self, "_" + k, part)
            
    def urls(self, urls = None):
        if urls is not None:
            return super(User, self).urls(urls)
        else:
            ret = super(User, self).urls()
            for part in self._parts.values():
                if hasattr(part, "urls") and callable(part.urls):
                    u = part.urls()
                    if u:
                        ret.append(u)
            return ret

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
