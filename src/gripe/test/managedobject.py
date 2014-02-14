'''
Created on Feb 10, 2014

@author: jan
'''
import unittest

import gripe.managedobject
import gripe.role

class MOTest(gripe.managedobject.ManagedObject):
    def __init__(self, labelval):
        self.label(labelval)

class Test(unittest.TestCase):
    def test_1_ManagedObject(self):
        mgr = MOTestManager()
        t = mgr.add("id", "label")
        print t, t.id(), t.label()

    def test_2_InitializeRoles(self):
        self.rolemanager = gripe.RoleManager()
        role = self.rolemanager.get("user")
        print role, role.id(), role.rolename(), role.label()
        
    def test_3_RoleAdd(self):
        self.rolemanager = gripe.RoleManager()
        role = self.rolemanager.add("test", **{ "label": "Test User", "has_roles": ["user", "admin"]})
        print role, role.id(), role.rolename(), role.label()
        
    def test_4_RoleAddExists(self):
        self.rolemanager = gripe.RoleManager()
        try:
            role = self.rolemanager.add("user")
            print role, role.id(), role.rolename(), role.label()
        except gripe.role.RoleExists as expected:
            pass
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()