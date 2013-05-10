# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Mar-2013 5:24:57 PM$"

import gripe
import gripe.url
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
            elif hasattr(self, "_roles"):
                return self._roles if self._roles else set()
            else:
                assert 0, "Class %s must implement either _explicit_roles() or provide a _roles attribute" % self.__class__.__name__

    def urls(self, urls = None):
        logger.debug("%s.urls(%s)", self, urls)
        if urls is not None:
            if isinstance(urls, (list, tuple)):
                self._urls = gripe.url.UrlCollection(str(self), None)
                self._urls.append(urls)
            if isinstance(urls, gripe.url.UrlCollection):
                self._urls = urls
            if isinstance(urls, dict):
                self._urls = gripe.url.UrlCollection(urls)
        ret = gripe.url.UrlCollection(self.__class__.__name__)
        if not hasattr(self, "_urls"):
            self._urls = None
        for role in self.role_objects():
            if hasattr(role, "_urls"):
                logger.info("urls: %s %s %s", self, role, type(role._urls))
                ret.append(role._urls() if callable(role._urls) else role._urls)
            else:
                assert 0, "Class %s must implement _urls as either a method or attribute" % role.__class__.__name__
        return ret

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

_role_manager = None

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
                # has_role = grit.Session.get_rolemanager().get_role(rname)
                has_role = _role_manager.get_role(rname)
                if has_role and has_role not in ret:
                    ret.add(has_role)
                    roles.append(has_role)
        return ret

class Role(AbstractRole):
    def __init__(self, role, has_roles, urls):
        self.role = role
        self._roles = has_roles
        logger.debug("Role.__init__(%s, %s, %s)", role, has_roles, urls)
        self.urls(urls)

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
        global _role_manager
        self._roles = {}
        _role_manager = self
        self.initialize()

    def add_role(self, role):
        self._roles[role.rolename()] = role

    def get_role(self, name):
        return self._roles.get(name)

    def initialize(self):
        if gripe.Config.app and "roles" in gripe.Config.app:
            for role in gripe.Config.app.roles:
                self.add_role(Role(role.role, role.has_roles, role.urls))
        else:
            logger.warn("No roles defined in app configuration")

if __name__ == "__main__":
    rolemanager = RoleManager()
    print rolemanager._roles
    admin = rolemanager.get_role('admin')
    print admin.urls()
