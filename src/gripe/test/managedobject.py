'''
Created on Feb 10, 2014

@author: jan
'''
import unittest

import gripe.managedobject
import gripe.role
import gripe.auth

@gripe.managedobject.configtag("unittest")
class SimpleManagedObject(gripe.managedobject.ManagedObject):
    pass

class TestRoles(unittest.TestCase):
    def test_1_ManagedObject(self):
        mgr = SimpleManagedObjectManager()
        t = mgr.add("id", label = "label")
        print t, t.objid(), t.objectlabel()

    def test_2_InitializeRoles(self):
        self.rolemanager = gripe.role.Guard.get_rolemanager()
        role = self.rolemanager.get("user")
        print role, role.objid(), role.rolename(), role.objectlabel()
        
    def test_3_RoleAdd(self):
        self.rolemanager = gripe.role.Guard.get_rolemanager()
        role = self.rolemanager.add("test", **{ "label": "Test User", "has_roles": ["user", "admin"]})
        print role, role.objid(), role.rolename(), role.objectlabel()
        
    def test_4_RoleAddExists(self):
        self.rolemanager = gripe.role.Guard.get_rolemanager()
        try:
            role = self.rolemanager.add("user")
            print role, role.objid(), role.rolename(), role.objectlabel()
        except gripe.role.RoleExists as expected:
            pass
        
class TestUsers(unittest.TestCase):
    def test_1_InitializeUsers(self):
        self.usermanager = gripe.role.Guard.get_usermanager()
        user = self.usermanager.get("jan@de-visser.net")
        print user, user.objid(), user.displayname(), user.roles(), user.groupnames()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()