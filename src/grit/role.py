# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Mar-2013 5:24:57 PM$"

import gripe
import grit

logger = gripe.get_logger("grit")

class HasRoles(object):
    def role_objects(self):
        assert 0, "Abstract method HasRoles.role_objects must be implemented in %s" % self.__class__

    def roles(self, explicit = False):
        """
            Returns the names of the roles self has in a set.
        """
        if not explicit:
            return {role.rolename() for role in self.role_objects()}
        else:
            if hasattr(self, "_explicit_roles") and callable(self._explicit_roles):
                return self._explicit_roles()
            elif hasattr(self, "has_roles"):
                return self.has_roles if self.has_roles else set()
            else:
                assert 0, "Class %s must implement either _explicit_roles() or provide a has_roles attribute" % self.__class__.__name__


    def has_role(self, roles):
        """
            Returns True if self has one or more roles listed in the roles
            parameter. 'roles' can either be a string denoting a single role
            name or an iterable of role names.
        """
        if isinstance(roles, basestring):
            roles = { roles }
        myroles = self.roles()
        logger.info("has_role: %s & %s = %s", set(roles), myroles, set(roles) & myroles)
        return len(set(roles) & myroles) > 0

class AbstractRole(HasRoles):
    def rolename(self):
        """
            Interface method returning the role name of self. Implementations
            of AbstractRole should provide this method.
        """
        assert 0, "Abstract AbstractRole.rolename called"

    def role_objects(self, include_self = True):
        roles = [self]
        ret = { self } if include_self else set()
        while roles:
            role = roles.pop()
            for rname in role.roles(explicit = True):
                has_role = grit.Session.get_rolemanager().get_role(rname)
                if has_role and has_role not in ret:
                    ret.add(has_role)
                    roles.append(has_role)
        return ret

class Role(AbstractRole):
    def __init__(self, role, has_roles):
        self.role = role
        self.has_roles = has_roles

    def __str__(self):
        return self.role

    def __repr__(self):
        return self.role

    def __eq__(self, other):
        return self.role == other.role if other.__class__ == Role else False

    def rolename(self):
        """
            Implementation of AbstractRole.rolename(). Returns the role attribute.
        """
        return self.role

class RoleManager(object):
    def __init__(self):
        self._roles = {}
        self.initialize()

    def add_role(self, role):
        self._roles[role.rolename()] = role

    def get_role(self, name):
        return self._roles.get(name)

    def initialize(self):
        if gripe.Config.app and "roles" in gripe.Config.app:
            for role in gripe.Config.app.roles:
                self.add_role(Role(role.role, role.has_roles))
        else:
            logger.warn("No roles defined in app configuration")

if __name__ == "__main__":
    print rolemanager._roles
