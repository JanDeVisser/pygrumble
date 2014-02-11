# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Mar-2013 5:24:57 PM$"

import gripe
import gripe.url

logger = gripe.get_logger("gripe")

class RoleExists(gripe.AuthException):
    def __init__(self, role):
        self._role = role

    def __str__(self):
        return "Role with ID %s already exists" % self._role
    
class RoleDoesntExist(gripe.AuthException):
    def __init__(self, role):
        self._role = role

    def __str__(self):
        return "Role with ID %s does not exists" % self._role
    
class AuthManagers(object):
    _managers = { }
    
    @classmethod
    def _get_manager(self, manager, default):
        if manager not in self:
            cls._managers[manager] = gripe.Config.resolve("app.%smanager" % manager, default)()
        return cls._managers[manager]

    @classmethod
    def get_usermanager(cls):
        return cls._get_manager("user", "gripe.auth.UserManager")

    @classmethod
    def get_usermanager(cls):
        return cls._get_manager("user", "gripe.auth.GroupManager")

    @classmethod
    def get_rolemanager(cls):
        return cls._get_manager("role", "gripe.role.RoleManager")

    @classmethod
    def get_sessionmanager(cls):
        return cls._get_manager("session", "grit.SessionManager")


@gripe.abstract("role_objects")
class HasRoles(gripe.ManagedObject):
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

                
    def add_role(self, role):
        """
            Assigns the provided role to self. The role can be provided as a string
            or as an AbstractRole object.
        """
        if isinstance(role, AbstractRole):
            r = role
            role = r.__id__()
        else:
            role = str(role)
            r = AuthManagers.get_rolemanager().get(role)
        if r:
            if hasattr(self, "_add_role") and callable(self._add_role):
                return self._add_role(role)
            elif hasattr(self, "_roles"):
                return self._roles.add(role)
            else:
                assert 0, "Class %s must implement either _add_role() or provide a _roles attribute" % self.__class__.__name__
                

    def urls(self, urls = None):
        if not hasattr(self, "_urls"):
            self._urls = gripe.url.UrlCollection(str(self), self.label())
        if urls is not None:
            self._urls.clear()
            if isinstance(urls, (list, tuple, set)):
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


@gripe.abstract("rolename")
class AbstractRole(HasRoles):
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
    def __init__(self, role, roledef):
        #self.add_role(Role(role.role, role.has_roles, role.urls))
        self.__id__(role)
        self.label(roledef.label if "label" in roledef else role)
        self._roles = set(roledef.has_roles) if "has_roles" in roledef else {}
        self.urls(roledef.urls if roledef.urls is not None else {})

    def rolename(self):
        """
            Implementation of AbstractRole.rolename(). Returns the role attribute.
        """
        return self.__id__()

@gripe.abstract("get", "add")
class AbstractRoleManager(object):
    pass

class RoleManager(object):
    _rolemanager = None
    
    def __init__(self):
        self._roles = {}
        self.initialize()

    def add(self, role, **kwargs):
        if self.get(role):
            logger.debug("UserManager.add(%s, %s) User exists", userid, password)
            raise RoleExists(role)
        else:
            role = Role(role, **kwargs)
            self._roles[role.rolename()] = role
            return role

    def get(self, name):
        return self._roles.get(name)
    
    def initialize(self):
        if gripe.Config.app and "roles" in gripe.Config.app:
            for role in gripe.Config.app.roles:
                self.add(role, **gripe.Config.app.roles[role])
        else:
            logger.warn("No roles defined in app configuration")
            
if __name__ == "__main__":
    rolemanager = RoleManager()
    print rolemanager._roles
    admin = rolemanager.get_role('admin')
    print admin.urls()
