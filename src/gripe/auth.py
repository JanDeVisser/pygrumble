# To change this template, choose Tools | Templates
# and open the template in the editor.

import random
import sys
import uuid

import gripe.role


__author__ = "jan"
__date__ = "$3-Mar-2013 10:11:27 PM$"

logger = gripe.get_logger("gripe")

class UserExists(gripe.AuthException):
    def __init__(self, uid):
        self._uid = uid
        logger.debug(str(self))

    def __str__(self):
        return "User with ID %s already exists" % self._uid

class UserDoesntExists(gripe.AuthException):
    def __init__(self, uid):
        self._uid = uid
        logger.debug(str(self))

    def __str__(self):
        return "User with ID %s doesn't exists" % self._uid

class InvalidConfirmationCode(gripe.AuthException):
    def __init__(self):
        logger.debug(str(self))

    def __str__(self):
        return "Invalid user confirmation code"

class BadPassword(gripe.AuthException):
    def __init__(self, uid):
        self._uid = uid
        logger.debug(str(self))

    def __str__(self):
        return "Bad password for user with ID %s" % self._uid


class AbstractAuthObject(gripe.role.HasRoles):
    def role_objects(self, include_self = True):
        s = set()
        for rname in self.roles(explicit = True):
            role = gripe.role.AuthManagers.get_rolemanager().get_role(rname)
            if role:
                s |= role.role_objects()
            else:
                logger.warn("Undefined role %s mentioned in '%s'.has_roles", rname, self.email)
        return s


@gripe.abstract("gid")
class AbstractUserGroup(AbstractAuthObject):
    def gid(self):
        return self.id()


class UserGroup(AbstractUserGroup):
    _groups = {}
    def __init__(self, group):
        self.id(group.get("groupid"))
        self._roles = group.get("has_roles")
        self._roles = self._roles or []
        UserGroup._groups[self.id()] = self

    @classmethod
    def get_group(cls, g):
        if isinstance(g, dict):
            gid = g.get("groupid")
        elif isinstance(g, AbstractGroup):
            gid = g.gid()
        else:
            gid = str(g)
        return UserGroup._groups.get(gid)

@gripe.abstract("get", "add")
class AbstractGroupManager(object):
    pass

class GroupManager(AbstractGroupManager):
    def get(cls, g):
        return UserGroup.get_groups.get(g)

    def add(self, **g):
        logger.debug("GroupManager.add(%s)", g)
        group = self.get(g)
        if group:
            raise gripe.auth.GroupExists(g)
        else:
            group = UserGroup(g)
            return group.gid()


@gripe.abstract("groups")
class AbstractUser(AbstractAuthObject):
    def role_objects(self, include_self = True):
        s = super(AbstractUser, self).role_objects()
        for g in self.groups():
            s |= g.role_objects()
        return s

    def uid(self):
        return self.id()

class User(AbstractUser):
    _users = {}

    def __init__(self, user):
        self.id(user.get("email"))
        self.display_name = user.get("display_name")
        self.password = user.get("password")
        self._roles = user.get("has_roles")
        self._roles = set(self._roles or [])
        self._groups = user.get("has_groups")
        self._groups = set(self._groups or [])
        User._users[self._id] = self

    def groups(self):
        ret = set()
        for gid in self._groups:
            group = UserGroup.get_group(gid)
            if group:
                ret.add()
        return ret

    @classmethod
    def get_user(cls, u):
        if isinstance(u, dict):
            uid = u.get("email")
        elif isinstance(u, AbstractUser):
            uid = u.uid()
        else:
            uid = str(u)
        logger.info("User.get_user(%s) registry %s", uid, User._users)
        return User._users.get(uid)


@gripe.abstract("get", "login", "add", "confirm", "changepwd")
class AbstractUserManager(object):
    def generate_password(self):
        return "".join(random.sample("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890.,!@#$%^&*()_+=-", 10))


class UserManager(AbstractUserManager):
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

    def get(self, u):
        return User.get_user(u)

    def login(self, userid, password):
        logger.info("UserManager.login(%s, %s)", userid, password)
        user = self.get(userid)
        logger.info("UserManager.login(%s, %s) -> %s", userid, password, user)
        return user if user and (user.password == password) else None

    def add(self, **u):
        user = self.get(u)
        if user:
            raise UserExists(u)
        else:
            user = User(u)
            return user.uid()

    def confirm(self, userid, status = 'Active'):
        logger.debug("UserManager.confirm(%s, %s)", userid, status)
        user = self.get(userid)
        if user:
            logger.debug("UserManager.confirm(%s, %s) OK", userid, status)
            user.status = status
        else:
            logger.debug("UserManager.confirm(%s, %s) doesn't exists", userid, status)
            raise UserDoesntExists(userid)

    def changepwd(self, userid, oldpassword, newpassword):
        logger.debug("UserManager.changepwd(%s, %s, %s)", userid, oldpassword, newpassword)
        user = self.login(userid, oldpassword)
        if user:
            logger.debug("UserManager.changepwd(%s, %s, %s) login OK. Changing pwd", userid, oldpassword, newpassword)
            user.password = newpassword
        else:
            raise BadPassword(userid)


if __name__ == "__main__":
#    groupmanager = GroupManager()
    usermanager = UserManager()
    print UserGroup._groups
    print User._users

    print User.get_user("jan@de-visser.net").roles(False)

