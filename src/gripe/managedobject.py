'''
Created on Feb 13, 2014

@author: jan
'''

import gripe

logger = gripe.get_logger("gripe")

class ObjectExists(gripe.AuthException):
    def __init__(self, cls, idval):
        self._cls = cls
        self._idval = idval
        logger.debug(str(self))

    def __str__(self):
        return "%s with ID %s already exists" % (self._cls.__name__, self._idval)


_temp_mo_meta = None

class ManagedObjectMetaClass(type):
    def __init__(cls, name, bases, dct):
        global _temp_mo_meta
        if _temp_mo_meta is not None:
            cls._mo_meta = _temp_mo_meta
        else:
            cls._mo_meta = { }
        _temp_mo_meta = None
        cls._objects = {}
        cls._accessors = {}
        
        def get(cls, val):
            if isinstance(val, dict):
                idval = val.get(cls._mo_meta.get("idprop", "id"))
            elif isinstance(val, cls):
                idval = val.__id__()
            else:
                idval = str(val)
            logger.debug("%s.get(%s) registry %s", cls.__name__, idval, cls._objects)
            return cls._objects.get(idval)
        cls.get = classmethod(get)
        
        def _set(cls, oldid, obj):
            if oldid and (oldid in cls._objects):
                del cls._objects[oldid]
            cls._objects[obj.__id__()] = obj
        cls._set = classmethod(_set)
        
        def add(clazz, idval, *args, **kwargs):
            if idval in clazz._objects:
                e = clazz._mo_meta.get("exists", ObjectExists)
                raise e(clazz, idval)
            obj = object.__new__(clazz)
            obj.id(idval)
            if hasattr(obj, "__init__"):
                obj.__init__(*args, **kwargs)
            return obj
        cls.add = classmethod(add)
        
        def objectmanager():
            if not(hasattr(cls, "_initialized")):
                cls._initialized = True
                objects = cls.__name__.lower() + "s"
                configtag = cls._mo_meta.get("configtag", "app")
                if configtag in gripe.Config and objects in gripe.Config[configtag]:
                    for idval in gripe.Config[configtag][objects]:
                        cls.add(idval, **gripe.Config[configtag][objects][idval])
                else:
                    logger.warn("No %s defined in app configuration" % objects)
            return cls
        mod = __import__(cls.__module__)
        setattr(mod, cls.__name__ + "Manager", objectmanager)

        
class mo_attr_assigner(object):
    def __init__(self, mo_attr, value = None):
        self.mo_attr = mo_attr
        self.value = value
        
    def __call__(self, obj):
        if isinstance(obj, type):
            obj._mo_meta[self.mo_attr] = self.value
            return obj
        else:
            return _mo_meta(self.mo_attr, method)
        
    def _mo_meta(self, value):
        global _temp_mo_meta
        if _temp_mo_meta is None:
            _temp_mo_meta = { }
        _temp_mo_meta[self.mo_attr] = value
        return obj


class idattr(mo_attr_assigner):
    def __init__(self, attrname = None):
        super(mo_attr_assigner, self).__init__("id", attrname)
        
class labelattr(mo_attr_assigner):
    def __init__(self, attrname = None):
        super(mo_attr_assigner, self).__init__("label", attrname)

class objectexists(mo_attr_assigner):
    def __init__(self, e):
        super(mo_attr_assigner, self).__init__("exists", e)
        

class ManagedObject(object):
    __metaclass__ = ManagedObjectMetaClass

    def __str__(self):
        return self.__id__()

    def __repr__(self):
        return self.__id__() or "<unassigned>"

    def __eq__(self, other):
        return self.__id__() == other.__id__() if self.__class__ == other.__class__ else False

    def __hash__(self):
        return self.__id__().__hash__()
    
    @classmethod
    def _get_method(cls, mo_attr):
        accessors = cls._accessors.get(mo_attr)
        if accessors is None:
            attr = cls._mo_meta.get(mo_attr, "_" + mo_attr)
            a = attr
            if isinstance(attr, basestring):
                a = hasattr(cls, attr) and getattr(cls, attr)
                a = callable(a) and a
            accessors = (attr, a)
            cls._accessors[mo_attr] = accessors
        return accessors

    def _get_attr_value(self, mo_attr):
        attr, a = self._get_method(mo_attr)
        return self.a() if a else ((hasattr(self, attr) and getattr(self, attr)) or None)

    def _set_attr_value(self, mo_attr, value):
        attr, a = self._get_method(mo_attr)
        if value is not None:
            if a:
                self.a(value)
            else:
                setattr(self, attr, value)

    def _setget_attr_value(self, mo_attr, value):
        self._set_attr_value(mo_attr, value)
        return self._get_attr_value(mo_attr)
    
    def __id__(self, idval = None):
        if idval is not None:
            oldid = self._get_attr_value("id")
            self._set_attr_value("id", idval)
            self.__class__._set(oldid, self)
        return self._get_attr_value("id")

    id = __id__

    def label(self, lbl = None):
        return self._setget_attr_value("label", lbl) or self.__id__()


