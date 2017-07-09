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


import gripe
import gripe.acl
import grumble.schema

logger = gripe.get_logger(__name__)

class ModelMetaClass(type):
    def __new__(cls, name, bases, dct):
        kind = type.__new__(cls, name, bases, dct)
        if name != 'Model':
            logger.debug("Creating new model class %s [%s]", name, bases)
            kind._sealed = False
            Registry.register(kind.__module__, name, kind)
            if "table_name" in dct:
                tablename = dct["table_name"]
            else:
                tablename = name
                kind.table_name = name
            kind._abstract = dct.get("_abstract", False)
            kind._flat = dct.get("_flat", False)
            kind._audit = dct.get("_audit", True)
            acl = gripe.Config.model["model"][name]["acl"] \
                if "model" in gripe.Config.model and \
                   name in gripe.Config.model["model"] and \
                   "acl" in gripe.Config.model["model"][name] \
                else dct.get("acl", None)
            kind._acl = gripe.acl.ACL(acl)
            kind._properties = {}
            kind._allproperties = {}
            kind._query_properties = {}
            mm = grumble.schema.ModelManager.for_name(kind._kind)
            mm.flat = kind._flat
            mm.audit = kind._audit
            mm.set_tablename(tablename)
            mm.kind = kind
            kind.modelmanager = mm
            for base in bases:
                if isinstance(base, ModelMetaClass) and base.__name__ != "Model":
                    kind._import_properties(base)
            for (propname, value) in dct.items():
                kind.add_property(propname, value)
            kind.customizer = gripe.Config.model["model"][name]["customizer"] \
                if "model" in gripe.Config.model and \
                    name in gripe.Config.model["model"] and \
                    "customizer" in gripe.Config.model["model"][name] \
                else dct.get("_customizer")
            kind.load_template_data()
        else:
            kind._acl = gripe.acl.ACL(gripe.Config.model.get("global_acl", kind.acl))
        return kind


class Registry(dict):
    def __init__(self):
        assert not hasattr(self.__class__, "_registry"), "grumble.meta.Registry is a singleton"

    @classmethod
    def _get_registry(cls):
        if not hasattr(cls, "_registry"):
            cls._registry = Registry() 
        return cls._registry
    
    @classmethod
    def register(cls, module, name, modelclass):
        assert modelclass, "Registry.register(): empty class name"
        reg = cls._get_registry()
        if not module:
            fullname = name
        else:
            module = module.lower()
            hierarchy = module.split(".")
            while hierarchy and hierarchy[0] in [ 'model', '__main__' ]:
                hierarchy.pop(0)
            hierarchy.append(name)
            fullname = ".".join(hierarchy)
        fullname = fullname.lower()
        assert fullname not in cls._get_registry(), "Registry.register(%s): Already registered" % fullname
        reg[fullname] = modelclass
        modelclass._kind = fullname

    @classmethod
    def fullname(cls, module, name):
        if not module:
            fullname = name
        else:
            hierarchy = module.split(".")
            while hierarchy and hierarchy[0] in [ 'model', '__main__' ]:
                hierarchy.pop(0)
            hierarchy.append(name)
            fullname = ".".join(hierarchy)
        fullname = fullname.lower()
        return fullname

    @classmethod
    def fullname_for_class(cls, modelclass):
        return Registry.fullname(modelclass.__module__, modelclass.__name__)

    @classmethod
    def get(cls, name):
        reg = cls._get_registry()
        # if empty - whatever we want it ain't there:
        assert reg, "Looking for kind %s but registry empty" % name
        if isinstance(name, ModelMetaClass):
            n = Registry.fullname_for_class(name)
            assert n in reg, "Requested grumble.meta.Registry entry for model class %s, but it is not in the registry" % n 
            return name
        elif isinstance(name.__class__, ModelMetaClass):
            n = Registry.fullname_for_class(name)
            assert n in reg, "Requested grumble.meta.Registry entry for model instance of class %s, but its class is not in the registry" % n 
            return name.__class__
        else:
            name = name.replace('/', '.').lower()
            if name.startswith("."):
                (empty, dot, name) = name.partition(".")
            if name.startswith("__main__."):
                (main, dot, name) = name.partition(".")
            ret = reg[name] if name in reg else None   # dict.get is shadowed.
            if not ret and "." not in name:
                e = ".%s" % name
                for n in reg:
                    if n.endswith(e):
                        c = reg[n]
                        assert not ret, "Registry.get(%s): Already found match %s but there's a second one %s" % \
                            (name, ret.kind(), c.kind())
                        ret = c
            if ret:
                return ret
            else:
                print "Going to fail for Registry.get(%s)" % name
                print "Current registry: %s" % reg
                raise NameError("kind(%s)" % name)

    @classmethod
    def subclasses(cls, rootclass):
        reg = cls._get_registry()
        ret = []
        for m in reg.values():
            if m != rootclass and issubclass(m, rootclass):
                ret.append(m)
        return ret

