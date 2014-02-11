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

    def __str__(self):
        return "User with ID %s already exists" % self._uid 

class UserDoesntExists(gripe.AuthException):
    def __init__(self, uid):
        self._uid = uid

    def __str__(self):
        return "User with ID %s doesn't exists" % self._uid

class InvalidConfirmationCode(gripe.AuthException):
    def __str__(self):
        return "Invalid user confirmation code"

class BadPassword(gripe.AuthException):
    def __init__(self, uid):
        self._uid = uid

    def __str__(self):
        return "Bad password for user with ID %s" % self._uid 


class AbstractAuthObject(gripe.role.HasRoles):
    def role_objects(self, include_self = True):
        s = set()
        for rname in self.roles(explicit = True):
            role = gripe.role.RoleManager.get_rolemanager().get_role(rname)
            if role:
                s |= role.role_objects()
            else:
                logger.warn("Undefined role %s mentioned in '%s'.has_roles", rname, self.email)
        return s


@gripe.abstract("gid")
class AbstractUserGroup(AbstractAuthObject):
    _idattr = "gid"

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

@gripe.abstract("get", "add")
class AbstractGroupManager(object):
    def get(cls, id):
        return UserGroup._groups.get(id)

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


@gripe.abstract("uid", "groups")
class AbstractUser(AbstractAuthObject):
    _idattr = "uid"
    
    def role_objects(self, include_self = True):
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
        self._roles = set(self._roles or [])
        self._groups = user.get("has_groups")
        self._groups = set(self._groups or [])
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

    def get(self, userid):
        return User.get_user(userid)

    def login(self, userid, password):
        logger.info("UserManager.login(%s, %s)", userid, password)
        user = self.get(userid)
        logger.info("UserManager.login(%s, %s) -> %s", userid, password, user)
        return user if user and (user.password == password) else None

    def add(self, userid, password, display_name = None):
        user = self.get(userid)
        if user:
            logger.debug("UserManager.add(%s, %s) User exists", userid, password)
            raise UserExists(userid)
        else:
            u = { "email": userid, "password": password, "display_name": display_name }
            User(u)
        
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

