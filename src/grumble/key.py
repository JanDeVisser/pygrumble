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
        if len(args) == 1:
            value = args[0]
            assert value is not None, "Cannot initialize Key from None"
            if isinstance(value, basestring):
                self._assign(value)
            elif isinstance(value, dict):
                if "id" in dict:
                    self.__init__(dict[id])
                else:
                    self.__init__(dict["kind"], dict["name"])
            elif hasattr(value, "key") and callable(value.key):
                k = value.key()
                self.kind = k.kind
                self.id = k.id
                self.name = k.name
            else:
                assert 0, "Cannot initialize Key from %s, type %s" % (value, type(value))
            if not (hasattr(self, "id") and self.id) and self.name and self.kind:
                self.id = base64.urlsafe_b64encode("%s:%s" % (self.kind, self.name))
        elif len(args) == 2:
            kind = args[0]
            assert (isinstance(kind, basestring) or
                   (hasattr(kind, "kind") and callable(kind.kind))), \
                   "First argument of Key(kind, name) must be string or model class, not %s" % type(args[0])
            assert isinstance(args[1], basestring), \
                   "Second argument of Key(%s, name) must be string, not %s" % (kind, type(args[1]))
            self._assign("%s:%s" % (kind if isinstance(kind, basestring) else kind.kind(), args[1]))

    def _assign(self, value):
        value = str(value)
        if value.count(":"):
            s = value
            self.id = base64.urlsafe_b64encode(value)
        else:
            self.id = value
            s = base64.urlsafe_b64decode(value)
        (k, _, n) = s.partition(":")
        self.name = urllib.unquote_plus(n)
        self.kind = grumble.meta.Registry.get(k).kind()

    def __str__(self):
        return self.kind + ":" + urllib.quote_plus(self.name)

    def __call__(self):
        return self.get()
    
    def key(self):
        return self
    
    def modelclass(self):
        return grumble.meta.Registry.get(self.kind)

    def __eq__(self, other):
        if not isinstance(other, Key) and hasattr(other, "key") and callable(other.key):
            return self.__eq__(other.key())
        else:
            if not other:
                return False
            assert isinstance(other, Key), "Can't compare key '%s' and %s '%s'" % (self, other.__class__, other)
            return (self.kind == other.kind) and (self.name == other.name)

    def __hash__(self):
        return hash(str(self))

    def get(self):
        cls = grumble.meta.Registry.get(self.kind)
        return cls.get(self)

