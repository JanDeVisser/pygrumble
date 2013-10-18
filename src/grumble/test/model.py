#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$18-Sep-2013 8:57:43 AM$"

import sys

if __name__ != '__main__' and __name__ != 'model':
    print __name__
    print "Get off my lawn, punk!"
    sys.exit(0)

import gripe.pgsql
import grumble

with gripe.pgsql.Tx.begin():
    class Test(grumble.Model):
        testname = grumble.TextProperty(required = True, is_label = True)
        value = grumble.IntegerProperty(default = 12)

    jan = Test(testname = "Jan", value = "42")
    assert jan.id() is None
    assert jan.testname == "Jan"
    assert jan.value == 42
    jan.put()
    assert jan.id() is not None, "jan.id() is still None after put()"
    x = jan.key()

with gripe.pgsql.Tx.begin():
    y = Test.get(x)
    assert y.id() == x.id
    assert y.testname == "Jan"
    assert y.value == 42
    y.value = 43
    y.put()
    assert y.value == 43

with gripe.pgsql.Tx.begin():
    tim = Test(testname = "Tim", value = 9, parent = y)
    tim.put()
    assert tim.parent().id == y.id()

    gripe.pgsql.Tx.flush_cache()
    q = grumble.Query(Test)
    for t in q:
        print t.testname

    gripe.pgsql.Tx.flush_cache()
    q = grumble.Query(Test, False)
    for t in q:
        print t.testname

    print Test.all().count()
    for t in Test.all():
        print t.testname

    count = Test.count()
    assert count == 2, "Expected Test.count() to return 2, but it returned %s instead" % count

    class Test2(grumble.Model):
        testname = grumble.TextProperty(required = True, is_label = True)
        value = grumble.IntegerProperty(default = 12)
    mariska = Test2(testname = "Mariska", value = 40, parent = y)
    mariska.put()

    class Test3(grumble.Model):
        testname = grumble.TextProperty(required = True, is_label = True)
        value = grumble.IntegerProperty(default = 12)
    jeroen = Test3(testname = "Jeroen", value = 44, parent = y)
    jeroen.put()

    print ">>> Test, Test2, Test3 with ancestor"
    q = grumble.Query((Test, Test2, Test3), False, ancestor = y)
    for t in q:
        print t.testname


    print ">>> Test2, Test3 with ancestor"
    q = grumble.Query((Test2, Test3), False, ancestor = y)
    for t in q:
        print t.testname

    print "<<<"

    print ">>> Subclassing models"
    class Test3Sub(Test3):
        lightswitch = grumble.BooleanProperty(default = False)

    t3s = Test3Sub(testname = "T3S", value = "3", lightswitch = True)
    t3s.put()
    print t3s.testname, t3s.value, t3s.lightswitch
    q = grumble.Query(Test3, False)
    for t in q:
        print t.testname
    print "<<<"

    class RefTest(grumble.Model):
        refname = grumble.TextProperty(required = True, is_key = True)
        ref = grumble.ReferenceProperty(Test)

    print ">>", jan, jan.id()
    r = RefTest(refname = "Jan", ref = jan)
    print "-->", r.refname, r.ref
    r.put()

    q = grumble.Query(Test)
    q.set_ancestor("/")
    for t in q:
        print t

    q = grumble.Query(Test)
    q.set_ancestor(y)
    for t in q:
        print t

    q = grumble.Query(Test)
    q.add_filter("value = ", 9)
    q.get()

    q = grumble.Query(Test)
    q.set_ancestor(y)
    q.add_filter("testname = ", 'Tim')
    q.add_filter("value < ", 10)
    for t in q:
        print t

    q = grumble.Query(RefTest)
    q.add_filter("ref = ", y)
    for t in q:
        print t

    y.reftest_set.run()

    class SelfRefTest(grumble.Model):
        selfrefname = grumble.TextProperty(key = True, required = True)
        ref = grumble.SelfReferenceProperty(collection_name = "loves")

    luc = SelfRefTest(selfrefname = "Luc")
    luc.put()

    schapie = SelfRefTest(selfrefname = "Schapie", ref = luc)
    schapie.put()
    print schapie.to_dict()

    for s in luc.loves:
        print s

    luc.ref = schapie
    luc.put()
    print schapie.to_dict()
    print luc.to_dict()
