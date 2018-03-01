# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 11:22:38 AM$"

import gripe

class PropertyRequired(gripe.Error):
    """Raised when no value is specified for a required property"""
    def __init__(self, propname):
        self.propname = propname

    def __str__(self):
        return "Property %s requires a value" % (self.propname,)


class InvalidChoice(gripe.Error):
    """Raised when a value is specified for a property that is not in the
    property's <tt>choices</tt> list"""
    def __init__(self, propname, value):
        self.propname = propname
        self.value = value

    def __str__(self):
        return "Value %s is invalid for property %s" % \
            (self.value, self.propname)


class OutOfRange(gripe.Error):
    """Raised when a value is out of range"""
    def __init__(self, propname, value):
        self.propname = propname
        self.value = value

    def __str__(self):
        return "Value %s out of range for property %s" % \
            (self.value, self.propname)


class ObjectDoesNotExist(gripe.Error):
    """Raised when an object is requested that does not exist"""
    def __init__(self, cls, id):
        self.cls = cls
        self.id = id

    def __str__(self):
        return "Model %s:%s does not exist" % (self.cls.__name__, self.id)


class KeyPropertyRequired(gripe.Error):
    """Raised when an object stored but the key property is not set (None)"""
    def __init__(self, cls, propname):
        self.cls = cls
        self.propname = propname

    def __str__(self):
        return "Key property '%s' not set when storing model '%s'" % (self.propname, self.cls)

class PatternNotMatched(gripe.Error):
    """Raised when an object stored but the key property is not set (None)"""
    def __init__(self, propname, value):
        self.propname = propname
        self.value = value

    def __str__(self):
        return "String '%s' does match required pattern for property '%s'" % (self.value, self.propname)
