# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 8:38:26 PM$"

import base64
import urllib
import grumble.meta

class Key(object):
    def __new__(cls, *args):
        if (len(args) == 1) and hasattr(args[0], "key") and callable(args[0].key):
            return args[0].key()
        else:
            return super(Key, cls).__new__(cls)

    def __init__(self, *args):
        assert args, "Cannot construct void Key"
        if len(args) == 1:
            value = args[0]
            assert value is not None, "Cannot initialize Key from None"
            if isinstance(value, basestring):
                self._assign(value)
            elif isinstance(value, dict):
                if "id" in dict:
                    self.__init__(dict[id])
                else:
                    self.__init__(dict["kind"], dict["name"], dict.get("scope"))
            elif hasattr(value, "key") and callable(value.key):
                k = value.key()
                self.kind = k.kind
                self.id = k.id
                self.name = k.name
                self._scope = k._scope
            else:
                assert 0, "Cannot initialize Key from %s, type %s" % (value, type(value))
        else:
            kind = args[0]
            assert (isinstance(kind, basestring) or
                   (hasattr(kind, "kind") and callable(kind.kind))), \
                   "First argument of Key(kind, name) must be string or model class, not %s" % type(args[0])
            assert isinstance(args[-1], basestring), \
                   "Last argument of Key(%s, ..., name) must be string, not %s" % (kind, type(args[1]))
            if len(args) == 2:
                self._assign("%s:%s" % (kind if isinstance(kind, basestring) else kind.kind(), urllib.quote_plus(str(args[1]))))
            elif len(args) == 3:
                self._assign("%s:%s:%s" % (kind if isinstance(kind, basestring) else kind.kind(), 
                    urllib.quote_plus(str(args[1])) if args[1] else "", 
                    urllib.quote_plus(str(args[2]))))
        if not (hasattr(self, "id") and self.id):
            self.id = base64.urlsafe_b64encode(str(self))

    def _assign(self, value):
        value = str(value)
        arr = value.split(":")
        if len(arr) == 1:
            self._assign(base64.urlsafe_b64decode(value))
        else:
            self.id = base64.urlsafe_b64encode(value)
            self.kind = grumble.meta.Registry.get(arr[0]).kind()
            assert self.kind, "Cannot parse key %s: unknown kind %s" % (value, arr[0])
            self.name = urllib.unquote_plus(arr[-1])
            if len(arr) == 3:
                self._scope = urllib.unquote_plus(arr[1])
            else:
                self._scope = None

    def __str__(self):
        return (
            "%s:%s:%s" % (self.kind, urllib.quote_plus(self._scope), urllib.quote_plus(self.name)) if self._scope is not None
            else "%s:%s" % (self.kind, urllib.quote_plus(self.name)))

    def __call__(self):
        return self.get()
    
    def key(self):
        return self
    
    def deref(self):
        return self.get()
    
    def basekind(self):
        (_, _, k) = self.kind.rpartition(".")
        return k
    
    def modelclass(self):
        return grumble.meta.Registry.get(self.kind)
    
    def scope(self):
        return Key(self._scope) if self._scope else None
    
    def __eq__(self, other):
        if not(isinstance(other, Key)) and hasattr(other, "key") and callable(other.key):
            return self == other.key()
        else:
            if not(other or isinstance(other, Key)):
                return False
            else:
                return (self.kind == other.kind) and (self.name == other.name)

    def __hash__(self):
        return hash(str(self))

    def get(self):
        cls = grumble.meta.Registry.get(self.kind)
        return cls.get(self)

