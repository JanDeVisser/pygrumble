# To change this template, choose Tools | Templates
# and open the template in the editor.

import uuid
import random

import gripe
import grit.role


__author__ = "jan"
__date__ = "$3-Mar-2013 10:11:27 PM$"

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
                logger.warn("Undefined role %s mentioned in '%s'.has_roles", rname, self.email)
        return s


class AbstractUserGroup(AbstractAuthObject):
    def gid(self):
        assert 0, "Abstract method AbstractUserGroup.gid() must be implemented in class %s" % self.__class__


class UserGroup(AbstractUserGroup):
    _groups = {}
    def __init__(self, group):
        self._id = group.get("groupid")
        self._roles = group.get("has_roles")
        self._roles = self._roles or []
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
        self._roles = user.get("has_roles")
        self._roles = self._roles or []
        self._groups = user.get("has_groups")
        self._groups = self._groups or []
        User._users[self._id] = self

    def uid(self):
        return self._id

    def groups(self):
        ret = set()
        for gid in self._groups:
            group = UserGroup.get_group(gid)
            if group:
                ret.add()
        return ret

    @classmethod
    def get_user(cls, id):
        logger.info("User.get_user(%s) registry %s", id, User._users)
        return User._users.get(id)

class AbstractUserManager(object):
    def confirmation_code(self):
        return uuid.uuid1().hex

    def gen_password(self):
        return "".join(random.sample("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890!@#$%^&*()_+=-", 10))

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

    def admin_pwd_reset(self, userid):
        assert 0, "Abstract method AbstractUserManager.admin_pwd_reset must be implemented for class %s" % self.__class__

    def request_pwd_reset(self, userid):
        assert 0, "Abstract method AbstractUserManager.request_pwd_reset must be implemented for class %s" % self.__class__

    def confirm_pwd_reset(self, userid, code, newpasswd):
        assert 0, "Abstract method AbstractUserManager.confirm_pwd_reset must be implemented for class %s" % self.__class__

class UserManager(AbstractUserManager):
    _pwd_resets = { }

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
        return User.get_user(userid)

    def login(self, userid, password):
        logger.info("UserManager.login(%s, %s)", userid, password)
        user = self.get(userid)
        logger.info("UserManager.login(%s, %s) -> %s", userid, password, user)
        return user if user and (user.password == password) else None

    def admin_pwd_reset(self, userid):
        user = self.get(userid)
        if user:
            newpasswd = self._gen_password()
            user.password = newpasswd
            return newpasswd
        else:
            return None

    def request_pwd_reset(self, userid):
        user = self.get(userid)
        if user:
            code = self._confirmation_code()
            UserManager._pwd_resets[code] = userid
            return code
        else:
            return None

    def confirm_pwd_reset(self, userid, code, newpasswd):
        if userid and code:
            if UserManager._pwd_resets.get(code) != userid:
                return False
            else:
                user = self.get(userid)
                user.password = newpasswd
                return True
        else:
            return False

if __name__ == "__main__":
#    groupmanager = GroupManager()
    usermanager = UserManager()
    print UserGroup._groups
    print User._users

    print User.get_user("jan@de-visser.net").roles(False)

