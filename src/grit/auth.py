# To change this template, choose Tools | Templates
# and open the template in the editor.

import gripe
import grit.role

__author__="jan"
__date__ ="$3-Mar-2013 10:11:27 PM$"

logger = gripe.get_logger("grit")

class AbstractAuthObject(grit.role.HasRoles):
    def __str__(self):
        return self.__id__()

    def __repr__(self):
        return self.__id__()

    def __eq__(self, other):
        return self.__id__() == other.__id__() if self.__class__ == other.__call__ else False

    def __id__(self):
        if hasattr(self, "uid") and callable(self.uid):
            return self.uid()
        elif hasattr(self, "gid") and callable(self.gid):
            return self.gid()
        elif hasattr(self, "_id"):
            return self._id
        else:
            return str(hash(self))

    def role_objects(self):
        s = set()
        for rname in self.roles(explicit = True):
            role = grit.Session.get_rolemanager().get_role(rname)
            if role:
                s |= role.role_objects()
            else:
                logging.warn("Undefined role %s mentioned in '%s'.has_roles", rname, self.email)
        return s


class AbstractUserGroup(AbstractAuthObject):
    def gid(self):
        assert 0, "Abstract method AbstractUserGroup.gid() must be implemented in class %s" % self.__class__


class UserGroup(AbstractUserGroup):
    _groups = {}
    def __init__(self, group):
        self._id = group.get("groupid")
        self.has_roles = group.get("has_roles")
        self.has_roles = self.has_roles or []
        UserGroup._groups[self._id] = self

    def gid(self):
        return self._id

    @classmethod
    def get_group(cls, id):
        return UserGroup._groups.get(id)


class AbstractUser(AbstractAuthObject):
    def uid(self):
        assert 0, "Abstract method AbstractUser.uid() must be implemented in class %s" % self.__class__

    def groups(self):
        assert 0, "Abstract method AbstractUser.groups() must be implemented in class %s" % self.__class__

    def role_objects(self):
        s = super(AbstractUser, self).role_objects()
        for g in self.groups():
            s |= g.role_objects()
        return s

class User(AbstractUser):
    _users = {}
    def __init__(self, user):
        self._id = user.get("email")
        self.display_name = user.get("display_name")
        self.password = user.get("password")
        self.has_roles = user.get("has_roles")
        self.has_roles = self.has_roles or []
        self.has_groups = user.get("has_groups")
        self.has_groups = self.has_groups or []
        User._users[self._id] = self

    def uid(self):
        return self._id

    def groups(self):
        ret = set()
        for gid in self.has_groups:
            group = UserGroup.get_group(gid)
            if group:
                ret.add()
        return ret

    @classmethod
    def get_user(cls, id):
        logger.info("User.get_user(%s) registry %s", id, User._users)
        return User._users.get(id)

    @classmethod
    def login(cls, id, password):
        logger.info("User.login(%s, %s)", id, password)
        user = cls.get_user(id)
        logger.info("User.login(%s, %s) -> %s", id, password, user)
        return user if user and (user.password == password) else None

class AbstractUserManager(object):
    def __init__(self):
        logger.info("Config.users %s", gripe.Config.users)
        if gripe.Config.users and hasattr(gripe.Config.users, "groups"):
            for group in gripe.Config.users.groups:
                UserGroup(group)
        if gripe.Config.users and hasattr(gripe.Config.users, "users"):
            for user in gripe.Config.users.users:
                User(user)
        else:
            logger.warn("No users tag in users.json configuration file")

    def get(self, userid):
        assert 0, "Abstract method AbstractUserManager.get must be implemented for class %s" % self.__class__

    def login(self, userid, password):
        assert 0, "Abstract method AbstractUserManager.login must be implemented for class %s" % self.__class__

    def uid(self, user):
        return user.uid() if user else None

    def displayname(self, user):
        if not user:
            return None
        elif hasattr(user, "displayname") and callable(user.displayname):
            return user.displayname()
        elif hasattr(user, "display_name"):
            return user.display_name
        elif hasattr(user, "name"):
            return user.name
        else:
            return user.uid()

    def roles(self, user):
        return user.roles() if user else set()

    def has_role(self, user, roles):
        return user.has_role(roles) if user else False

class UserManager(AbstractUserManager):
    def get(self, userid):
        return User.get_user(userid)

    def login(self, userid, password):
        return User.login(userid, password)

if __name__ == "__main__":
    print "Hello World";
