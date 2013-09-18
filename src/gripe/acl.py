# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 8:36:18 PM$"

import json

class ACL(object):
    def __init__(self, acl):
        self.set(acl)
        
    def set(self, acl):
        if isinstance(acl, dict):
            self._acl = dict(acl)
        elif isinstance(acl, basestring):
            self._acl = json.loads(acl)
        else:
            self._acl = {}
        for (role, perms) in self._acl.items():
            assert role and role.lower() == role, "ACL.set_acl: Role may not be None and and must be lower case"
            assert perms and perms.upper() == perms, "ACL.set_acl: Permissions may not be None and must be upper case"
            
    def acl(self):
        if not hasattr(self, "_acl"):
            self.set_acl(None)
        return self._acl
    
    def __call__(self):
        return self.acl()

    def set_ace(self, role, perms):
        assert role, "ACL.set_ace: Role must not be None"
        if not hasattr(self, "_acl"):
            self.set_acl(None)
        perms = "".join(perms)
        self.acl()[role.lower()] = perms.upper() if perms else ""

    def get_ace(self, role):
        assert role, "ACL.set_ace: Role must not be None"
        if not hasattr(self, "_acl"):
            self.set_acl(None)
        return set(self.acl().get(role.lower(), ""))

    def to_json(self):
        return json.dumps(self.acl())