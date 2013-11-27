# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Mar-2013 5:24:57 PM$"

import gripe.url

logger = gripe.get_logger("gripe")

class HasRoles(object):
    def role_objects(self, include_self = True):
        assert 0, "Abstract method HasRoles.role_objects must be implemented in %s" % self.__class__

    def __str__(self):
        return self.__id__()

    def __repr__(self):
        return self.__id__()

    def __eq__(self, other):
        return self.__id__() == other.__id__() if self.__class__ == other.__class__ else False

    def __id__(self, id = None):
        idattr = self._idattr if hasattr(self, "_idattr") else None
        if id is not None and idattr is not None:
            if hasattr(self, idattr) and callable(getattr(self, idattr)):
                getattr(self, idattr)(id)
            else:
                setattr(self, idattr, id)             
        if idattr is not None:
            if not hasattr(self, idattr):
                return None
            elif callable(getattr(self, idattr)):
                return getattr(self, idattr)()
            else:
                return getattr(self, idattr) 
        else:
            return str(hash(self))

    def label(self, lbl = None):
        if lbl is not None:
            self._label = lbl
        elif not hasattr(self, "_label"):
            self._label = str(self)
        return self._label

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
        if not hasattr(self, "_urls"):
            self._urls = gripe.url.UrlCollection(str(self), self.label())
        if urls is not None:
            self._urls.clear()
            if isinstance(urls, (list, tuple)):
                self._urls.append(urls)
            elif isinstance(urls, gripe.url.UrlCollection):
                self._urls.copy(urls)
            elif isinstance(urls, dict):
                if urls.get("urls") is not None:
                    self._urls.append(urls["urls"])
            else:
                assert 0, "[%s]%s: Cannot initialize urls with %s" % (self.__class__.__name__, self, urls)
            logger.debug("%s._urls = %s (From %s)", self, self._urls, urls)
        ret = gripe.url.UrlCollection(self._urls)
        for role in self.role_objects(False):
            ret.append(role._urls)
        logger.debug("%s.urls() = %s", self, ret)
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
                has_role = RoleManager.get_rolemanager().get_role(rname)
                if has_role and has_role not in ret:
                    ret.add(has_role)
                    roles.append(has_role)
        return ret

class Role(AbstractRole):
    _idattr = "_role"

    def __init__(self, role, roledef):
        #self.add_role(Role(role.role, role.has_roles, role.urls))
        self.__id__(role)
        self.label(roledef.label if "label" in roledef else role)
        self._roles = roledef.has_roles if "has_roles" in roledef else []
        self.urls(roledef.urls if roledef.urls is not None else {})

    def rolename(self):
        """
            Implementation of AbstractRole.rolename(). Returns the role attribute.
        """
        return self.__id__()

class RoleManager(object):
    _rolemanager = None
    
    def __init__(self):
        self._roles = {}
        self.__class__._rolemanager = self
        self.initialize()

    def add_role(self, role):
        self._roles[role.rolename()] = role

    def get_role(self, name):
        return self._roles.get(name)

    def initialize(self):
        if gripe.Config.app and "roles" in gripe.Config.app:
            for role in gripe.Config.app.roles:
                self.add_role(Role(role, gripe.Config.app.roles[role]))
        else:
            logger.warn("No roles defined in app configuration")
            
    @classmethod
    def get_rolemanager(cls):
        ret = cls._rolemanager
        if ret is None:
            RoleManager()
            ret = cls._rolemanager
        return ret

if __name__ == "__main__":
    rolemanager = RoleManager()
    print rolemanager._roles
    admin = rolemanager.get_role('admin')
    print admin.urls()
