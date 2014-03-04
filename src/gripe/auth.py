# To change this template, choose Tools | Templates
# and open the template in the editor.

import random
import sys
import uuid

import gripe.role


__author__ = "jan"
__date__ = "$3-Mar-2013 10:11:27 PM$"

logger = gripe.get_logger("gripe")

#############################################################################
# E X C E P T I O N S
#############################################################################

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

class GroupExists(gripe.AuthException):
    def __init__(self, gid):
        self._gid = gid
        logger.debug(str(self))

    def __str__(self):
        return "Group with ID %s already exists" % self._gid

class GroupDoesntExists(gripe.AuthException):
    def __init__(self, gid):
        self._gid = gid
        logger.debug(str(self))

    def __str__(self):
        return "Group with ID %s doesn't exists" % self._gid


#############################################################################
# A B S T R A C T  C L A S S E S
#############################################################################


class AbstractAuthObject(gripe.role.Principal):
    def role_objects(self, include_self = True):
        s = set()
        for rname in self.roles(explicit = True):
            role = gripe.role.Guard.get_rolemanager().get(rname)
            if role:
                s |= role.role_objects()
            else:
                logger.warn("Undefined role %s mentioned in '%s'.has_roles", rname, self.email)
        return s


@gripe.abstract("gid")
class AbstractUserGroup(AbstractAuthObject):
    def authenticate(self, **kwargs):
        return False

@gripe.abstract("groupnames")
@gripe.abstract("uid")
@gripe.abstract("displayname")
@gripe.abstract("confirm")
@gripe.abstract("changepwd")
class AbstractUser(AbstractAuthObject):
    def role_objects(self, include_self = True):
        s = super(AbstractUser, self).role_objects()
        for g in self.groups():
            s |= g.role_objects()
        return s

    def groups(self):
        ret = set()
        for gid in self.groupnames():
            group = gripe.role.Guard.get_groupmanager().get(gid)
            if group:
                ret.add()
        return ret
    
    def logged_in(self, session):
        pass

    def logged_out(self, session):
        pass

    @classmethod
    def generate_password(cls):
        return "".join(random.sample("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890.,!@#$%^&*()_+=-", 10))


#############################################################################
# I M P L E M E N T A T I O N  C L A S S E S
#############################################################################

@gripe.managedobject.objectexists(GroupExists)
@gripe.managedobject.configtag("users")
class UserGroup(AbstractUserGroup, gripe.role.ManagedPrincipal):
    def gid(self):
        return self.objid()

@gripe.managedobject.objectexists(UserExists)
@gripe.managedobject.idattr("email")
@gripe.managedobject.labelattr("display_name")
@gripe.managedobject.configtag("users")
class User(AbstractUser, gripe.role.ManagedPrincipal):
    def __initialize__(self, **user):
        self._groups = user.pop("has_groups") if "has_groups" in user else []
        self._groups = set(self._groups)
        user = super(User, self).__initialize__(**user)
        return user

    def uid(self):
        return self.objid()
    
    def displayname(self):
        return self.objectlabel()

    def groupnames(self):
        return self._groups

    def authenticate(self, **kwargs):
        password = kwargs.get("password")
        logger.debug("User(%s).authenticate(%s)", self, password)
        return self.password == password

    def confirm(self, status = 'Active'):
        logger.debug("User(%s).confirm(%s)", self, status)
        self.status = status
        self.put()

    def changepwd(self, oldpassword, newpassword):
        logger.debug("User(%s).authenticate(%s)", self, oldpassword, newpassword)
        self.password = newpassword
        self.put()


if __name__ == "__main__":
    pass

