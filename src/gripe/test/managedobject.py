'''
Created on Feb 10, 2014

@author: jan
'''
import unittest

import gripe

class MOTest(gripe.ManagedObject):
    def __init__(self, idval, labelval):
        self.__id__(idval)
        self.label(labelval)

class Test(unittest.TestCase):

    def testName(self):
        t = MOTest("id", "label")
        print t, t.id(), t.label()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()