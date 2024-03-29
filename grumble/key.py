#
# Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#

import base64
import urllib

import gripe
import grumble.meta

logger = gripe.get_logger(__name__)


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
                if "id" in value:
                    self.__init__(value["id"])
                elif "key" in value:
                    self.__init__(value["key"])
                elif "kind" in value and "name" in value and "scope" in value:
                    self.__init__(value["kind"], value["name"], value.get("scope"))
                else:
                    assert 0, "Cannot create Key object from dict %s" % value
            elif hasattr(value, "key") and callable(value.key):
                k = value.key()
                self._kind = k.kind()
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
                self._assign("{:s}:{:s}".format( 
                     kind if isinstance(kind, basestring) else kind.kind(), 
                     urllib.quote_plus(str(args[1]))))
            elif len(args) == 3:
                p = args[1]
                p = (p.key() if hasattr(p, "key") and callable(p.key) else p) or ""
                self._assign("{:s}:{:s}:{:s}".format( 
                    kind if isinstance(kind, basestring) else kind.kind(),
                    urllib.quote_plus(str(p)),
                    urllib.quote_plus(str(args[2]))))
        if not (hasattr(self, "id") and self.id):
            self.id = base64.urlsafe_b64encode(str(self))

    def _assign(self, value):
        value = str(value)
        arr = value.split(":")
        if len(arr) == 1:
            try:
                self._assign(base64.urlsafe_b64decode(value))
            except TypeError:
                #logger.exception("Could not decode key '%s'", value)
                raise
        else:
            self.id = base64.urlsafe_b64encode(value)
            self._kind = grumble.meta.Registry.get(arr[0]).kind()
            assert self._kind, "Cannot parse key %s: unknown kind %s" % (value, arr[0])
            self.name = urllib.unquote_plus(arr[-1])
            if len(arr) == 3:
                self._scope = urllib.unquote_plus(arr[1])
            else:
                self._scope = None

    def __str__(self):
        return (
            "{:s}:{:s}:{:s}".format(
                self._kind, 
                urllib.quote_plus(self._scope), 
                urllib.quote_plus(self.name)) 
            if self._scope is not None
            else "{:s}:{:s}".format(
                self._kind,
                urllib.quote_plus(self.name)))

    def __call__(self):
        return self.get()
    
    def __getattr__(self, name):
        return getattr(self.get(), name)

    def key(self):
        return self

    def deref(self):
        return self.get()

    def kind(self):
        return self._kind

    def basekind(self):
        (_, _, k) = self.kind().rpartition(".")
        return k

    def samekind(self, model, sub = False):
        return self.modelclass().samekind(model, sub)

    def modelclass(self):
        return grumble.meta.Registry.get(self.kind())

    def scope(self):
        return Key(self._scope) if self._scope else None

    def __eq__(self, other):
        if not(isinstance(other, Key)) and hasattr(other, "key") and callable(other.key):
            return self == other.key()
        else:
            if not(other or isinstance(other, Key)):
                return False
            else:
                return (self.kind() == other.kind()) and (self.name == other.name)

    def __hash__(self):
        return hash(str(self))

    def get(self):
        cls = grumble.meta.Registry.get(self.kind())
        return cls.get(self)

