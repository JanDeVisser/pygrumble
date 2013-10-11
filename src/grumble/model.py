# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 11:41:49 AM$"

import base64
import json
import sys
import uuid

import gripe
import gripe.acl
import gripe.pgsql
import gripe.sessionbridge
import grumble.converter
import grumble.errors
import grumble.key
import grumble.meta
import grumble.property
import grumble.query
import grumble.schema

logger = gripe.get_logger(__name__)

class Model():
    __metaclass__ = grumble.meta.ModelMetaClass
    classes = {}
    acl = { "admin": "RUDQC", "owner": "R" }

    def __new__(cls, *args, **kwargs):
        cls.seal()
        ret = super(Model, cls).__new__(cls)
        ret._brandnew = True
        ret._set_ancestors_from_parent(kwargs["parent"] if "parent" in kwargs else None)
        ret._key_name = kwargs["key_name"] \
            if "key_name" in kwargs \
            else cls.get_new_key(kwargs) \
                 if hasattr(cls, "get_new_key") and callable(cls.get_new_key) \
                 else None
        ret._acl = gripe.acl.ACL(kwargs["acl"] if "acl" in kwargs else None)
        ret._id = None
        ret._values = {}
        for (propname, prop) in ret._allproperties.items():
            setattr(ret, propname, prop._initial_value())
        for (propname, propvalue) in kwargs.items():
            if propname in ret._allproperties:
                setattr(ret, propname, propvalue)
        logger.debug("%s.__new__: %s", ret.kind(), ret._values)
        return ret

    @classmethod
    def seal(cls):
        if not cls._sealed:
            cls._sealed = True
            cls.modelmanager.reconcile()


    def __repr__(self):
        return str(self.key())

    def __str__(self):
        self._load()
        label = self.label_prop if hasattr(self.__class__, "label_prop") else None
        if self.keyname():
            s = self.keyname()
            if label:
                s += " (%s)" % label
            return "<%s: %s>" % (self.kind(), s)
        else:
            super(self.__class__, self).__repr__()

    def __hash__(self):
        return hash(self.id())

    def __eq__(self, other):
        assert isinstance(other, Model)
        return (self.kind() == other.kind()) and (self.keyname() == other.keyname())

    def __call__(self):
        return self

    def _set_ancestors_from_parent(self, parent):
        if not self._flat:
            if parent:
                parent = parent.key()
            assert parent is None or isinstance(parent, grumble.key.Key)
            self._parent = parent
            if parent:
                p = parent.get()
                self._ancestors = p.path()
            else:
                self._ancestors = "/"
        else:
            self._parent = None
            self._ancestors = "/"

    def _set_ancestors(self, ancestors, parent):
        if not self._flat:
            if ancestors == "/":
                self._parent = None
                self._ancestors = "/"
            elif isinstance(ancestors, basestring):
                self._ancestors = ancestors
                (a, sep, p) = ancestors.rpartition("/")
                assert p == str(parent)
                self._parent = grumble.key.Key(p)
        else:
            self._parent = None
            self._ancestors = "/"

    def _populate(self, values):
        logger.debug("%s._populate(%s)", self.kind(), values)
        if values is not None:
            self._values = {}
            v = {}
            for (name, value) in values:
                v[name] = value
            parent = v["_parent"] if "_parent" in v else None
            ancestors = v["_ancestors"] if "_ancestors" in v else None
            self._key_name = v["_key_name"] if "_key_name" in v else None
            self._ownerid = v["_ownerid"] if "_ownerid" in v else None
            self._acl = gripe.acl.ACL(v["_acl"] if "_acl" in v else None)
            for prop in [p for p in self._properties.values() if not p.transient]:
                prop._update_fromsql(self, v)
            self._set_ancestors(ancestors, parent)
            logger.debug("%s._populate: _key_name: %s", self.kind(), self._key_name)
            logger.debug("%s._populate: hasattr(key_prop): %s", self.kind(), hasattr(self, "key_prop"))
            if (self._key_name is None) and hasattr(self, "key_prop"):
                logger.debug("Assigning key from key property: %s", self.key_prop)
                self._key_name = getattr(self, self.key_prop)
            else:
                logger.debug("No key prop. Using key_name %s", self._key_name)
            self._id = self.key().id
            self._exists = True
        else:
            self._exists = False

    def _load(self):
        #logger.debug("_load -> kind: %s, _id: %s, _key_name: %s", self.kind(), self._id, self._key_name)
        if (not(hasattr(self, "_values")) or (self._values is None)) and (self._id or self._key_name):
            self._populate(grumble.query.ModelQuery.get(self.key()))
        else:
            assert hasattr(self, "_values"), "Object of kind %s doesn't have _values" % self.kind()
            assert self._values is not None, "Object of kind %s has _values == None" % self.kind()
            assert hasattr(self, "_ancestors"), "Object of kind %s doesn't have _ancestors" % self.kind()
            assert hasattr(self, "_parent"), "Object of kind %s doesn't have _parent" % self.kind()

    def _store(self):
        self._load()
        logger.info("Storing model %s.%s", self.kind(), self.keyname())
        include_key_name = True
        if hasattr(self, "key_prop"):
            kp = getattr(self.__class__, self.key_prop)
            scoped = kp.scoped
            key = getattr(self, kp.name)
            if key is None:
                raise grumble.errors.KeyPropertyRequired(self.kind(), kp.name)
            self._key_name = "%s/%s" % (self.parent(), key) if scoped else key
            include_key_name = scoped
        elif not self._key_name:
            self._key_name = uuid.uuid1().hex
        self._id = None
        if hasattr(self, "_brandnew"):
            for prop in self._properties.values():
                prop._on_insert(self)
            if hasattr(self, "initialize") and callable(self.initialize):
                self.initialize()
        for prop in self._properties.values():
            prop._on_store(self)
        if hasattr(self, "on_store") and callable(self.on_store):
            self.on_store()
        self._validate()

        values = {}
        for prop in self._properties.values():
            prop._values_tosql(self, values)
        if include_key_name:
            values['_key_name'] = self._key_name
        if not self._flat:
            p = self.parent()
            values['_parent'] = str(p) if p else None
            values['_ancestors'] = self._ancestors
        values["_acl"] = self._acl.to_json()
        values["_ownerid"] = self._ownerid if hasattr(self, "_ownerid") else None
        grumble.query.ModelQuery.set(hasattr(self, "_brandnew"), self.key(), values)
        if hasattr(self, "_brandnew"):
            del self._brandnew
        for prop in self._properties.values():
            prop._after_store(self)
        if hasattr(self, "after_store") and callable(self.after_store):
            self.after_store()
        gripe.pgsql.Tx.put_in_cache(self)

    def _on_delete(self):
        return self.on_delete(self) if hasattr(self, "on_delete") and getattr(cls, "on_delete") else True

    def _validate(self):
        for prop in self._properties.values():
            prop.validate(prop.__get__(self, None))
        if hasattr(self, "validate") and callable(self.validate):
            self.validate()

    def id(self):
        if not self._id and self._key_name:
            self._id = self.key().id
        return self._id

    def keyname(self):
        return self._key_name

    def label(self):
        return self.label_prop if hasattr(self, "label_prop") else str(self)

    def parent(self):
        self._load()
        return self._parent

    def ancestors(self):
        """
            Returns the ancestor path of this Model object. This is the path 
            string of the parent object or empty if this object has no parent.
        """
        self._load()
        return self._ancestors if self._ancestors != "/" else ""

    def key(self):
        return grumble.key.Key(self.kind(), self._key_name) if self._key_name else None

    def path(self):
        a = self.ancestors()
        return (a if a != "/" else "") + "/" + str(self.key())

    def pathlist(self):
        pl = self.path().split("/")
        del pl[0]  # First element is "/" because the path starts with a "/"
        return [Model.get(k) for k in pl]

    def root(self):
        a = self.ancestors()
        if a:
            # ancestor path is not empty
            pl = self.path().split("/")
            del pl[0]  # First element is "/" because the path starts with a "/"
            rootkey = pl[0]
            return Model.get(rootkey)
        else:
            # ancestor path is empty, I am root
            return self

    def ownerid(self, oid = None):
        self._load()
        if oid is not None:
            self._ownerid = oid
        return self._ownerid

    def put(self):
        self._store()

    def exists(self):
        if hasattr(self, "_brandnew"):
            return True
        else:
            self._load()
            return self._exists

    def _to_dict(self, d, **flags):
        pass

    def to_dict(self, **flags):
        with gripe.LoopDetector.begin() as detector:
            p = self.parent()
            ret = { "key": self.id(), 'parent': p.id if p else None }
            if self.id() in detector:
                logger.info("to_dict: Loop detected. %s is already serialized", self)
                return ret
            detector.add(self.id())
            logger.debug("to_dict: Added %s to loop detector", self)
            for b in self.__class__.__bases__:
                if hasattr(b, "_to_dict") and callable(b._to_dict):
                    b._to_dict(self, ret, **flags)

            def serialize(ret, (name, prop)):
                if prop.private:
                    return ret
                if hasattr(self, "to_dict_" + name) and callable(getattr(self, "to_dict_" + name)):
                    return getattr(self, "to_dict_" + name)(ret)
                else:
                    try:
                        return prop.to_json_value(self, ret)
                    except gripe.NotSerializableError:
                        pass

            ret = reduce(serialize, self.properties().items(), ret)
            ret = reduce(serialize, self._query_properties.items(), ret)
            hasattr(self, "sub_to_dict") and callable(self.sub_to_dict) and self.sub_to_dict(ret, **flags)
            return ret

    def _update(self, d):
        pass

    def update(self, descriptor, **flags):
        self._load()
        logger.info("Updating model %s.%s using descriptor %s", self.kind(), self.keyname(), descriptor)
        for b in self.__class__.__bases__:
            if hasattr(b, "_update") and callable(b._update):
                b._update(self, descriptor)
        for name, prop in filter(lambda (name, prop): (not prop.private) and (name in descriptor), self.properties().items()):
            newval = descriptor[name]
            logger.debug("Updating %s.%s to %s", self.kind(), name, newval)
            if hasattr(self, "update_" + name) and callable(getattr(self, "update_" + name)):
                getattr(self, "update_" + name)(descriptor)
            else:
                try:
                    prop.from_json_value(self, descriptor)
                except gripe.NotSerializableError:
                    pass
        self.put()
        if hasattr(self, "on_update") and callable(self.on_update):
            self.on_update(descriptor, **flags)
        return self.to_dict(**flags)

    def invoke(self, method, args, kwargs):
        self._load()
        args = args or []
        kwargs = kwargs or {}
        assert hasattr(self, method) and callable(getattr(self, method)), "%s.%s has not method %s. Can't invoke" % (self.kind(), self.key(), method)
        logger.info("Invoking %s on %s.%s using arguments *%s, **%s", method, self.kind(), self.key(), args, kwargs)
        return getattr(self, method)(*args, **kwargs)

    def get_user_permissions(self):
        roles = set(gripe.sessionbridge.get_sessionbridge().roles())
        if gripe.sessionbridge.get_sessionbridge().userid() == self.ownerid():
            roles.add("owner")
        roles.add("world")
        perms = set()
        for role in roles:
            perms |= self.get_all_permissions(role)
        return perms

    @classmethod
    def get_user_classpermissions(cls):
        roles = set(gripe.sessionbridge.get_sessionbridge().roles())
        roles.add("world")
        perms = set()
        for role in roles:
            perms |= cls.get_class_permissions(role) | Model.get_global_permissions(role)
        return perms

    def get_object_permissions(self, role):
        return self._acl.get_ace(role)

    @classmethod
    def get_class_permissions(cls, role):
        return cls._acl.get_ace(role)

    @staticmethod
    def get_global_permissions(role):
        return Model._acl.get_ace(role)

    def get_all_permissions(self, role):
        return self.get_object_permissions(role) | self.get_class_permissions(role) | self.get_global_permissions(role)

    def set_permissions(self, role, perms):
        self._acl.set_ace(role, perms)

    def can_read(self):
        return "R" in self.get_user_permissions()

    def can_update(self):
        return "U" in self.get_user_permissions()

    def can_delete(self):
        return "D" in self.get_user_permissions()

    @classmethod
    def can_query(cls):
        return "Q" in cls.get_user_classpermissions()

    @classmethod
    def can_create(cls):
        return "C" in cls.get_user_classpermissions()

    @classmethod
    def add_property(cls, propname, propdef):
        if not isinstance(propdef, (grumble.property.ModelProperty, grumble.property.CompoundProperty)):
            return
        logger.debug("'%s'.add_property('%s')", cls.__name__, propname)
        assert not cls._sealed, "Model %s is sealed. No more properties can be added" % cls.__name__
        if not hasattr(cls, propname):
            setattr(cls, propname, propdef)
        propdef.set_name(propname)
        propdef.set_kind(cls.__name__)
        mm = grumble.schema.ModelManager.for_name(cls._kind)
        if not propdef.transient:
            mm.add_column(propdef.get_coldef())
        if hasattr(propdef, "is_label") and propdef.is_label:
            #assert not hasattr(cls, "label_prop") or cls.label_prop.inherited_from, "Can only assign one label property"
            assert not propdef.transient, "Label property cannot be transient"
            cls.label_prop = propdef
        if hasattr(propdef, "is_key") and propdef.is_key:
            #assert not hasattr(cls, "key_prop") or cls.key_prop.inherited_from, "Can only assign one key property"
            assert not propdef.transient, "Key property cannot be transient"
            cls.key_prop = propname
        cls._properties[propname] = propdef
        cls._allproperties[propname] = propdef
        if isinstance(propdef, grumble.property.CompoundProperty):
            for p in propdef.compound:
                setattr(cls, p.name, p)
                cls._allproperties[p.name] = propdef

    @classmethod
    def _import_properties(cls, from_cls):
        for (propname, propdef) in from_cls.properties().items():
            cls.add_property(propname, grumble.property.ModelProperty(propdef))

    @classmethod
    def kind(cls):
        return cls._kind

    @classmethod
    def properties(cls):
        return cls._properties

    @classmethod
    def for_name(cls, name):
        return grumble.meta.Registry.get(name)

    @classmethod
    def subclasses(cls):
        return grumble.meta.Registry.subclasses(cls)

    @classmethod
    def get(cls, id, values = None):
        k = grumble.key.Key(id)
        if cls != Model:
            cls.seal()
            ret = gripe.pgsql.Tx.get_from_cache(k)
            if not ret:
                ret = super(Model, cls).__new__(cls)
                assert (cls.kind().endswith(k.kind)) or not k.kind, "%s.get(%s.%s) -> wrong key kind" % (cls.kind(), k.kind, k.name)
                ret._id = k.id
                ret._key_name = k.name
                if values:
                    ret._populate(values)
            else:
                # print "%s.get - Cache hit" % cls.__name__
                pass
        else:
            return k.modelclass().get(k, values)
        return ret

    @classmethod
    def get_by_key(cls, key):
        cls.seal()
        assert cls != Model, "Cannot use get_by_key on unconstrained Models"
        k = grumble.key.Key(cls, key)
        ret = gripe.pgsql.Tx.get_from_cache(k)
        if not ret:
            ret = super(Model, cls).__new__(cls)
            assert (cls.kind().endswith(k.kind)) or not k.kind, "%s.get_by_key(%s:%s) -> wrong key kind" % (cls.kind(), k.kind, k.name)
            ret._id = k.id
            ret._key_name = k.name
        return ret
    
    @classmethod
    def by(cls, property, value, **kwargs):
        cls.seal()
        assert cls != Model, "Cannot use by() on unconstrained Models"
        kwargs["keys_only"] = False
        q = cls.query('"%s" = ' % property, value, **kwargs)
        return q.get()

    @classmethod
    def query(cls, *args, **kwargs):
        cls.seal()
        logger.debug("%s.query: args %s kwargs %s", cls.__name__, args, kwargs)
        assert (args is None) or (len(args) % 2 == 0), "Must specify a value for every filter"
        assert cls != Model, "Cannot query on unconstrained Model class"
        q = Query(cls, kwargs.get("keys_only", True))
        if "ancestor" in kwargs and not cls._flat:
            q.set_ancestor(kwargs["ancestor"])
        if "parent" in kwargs and "ancestor" not in kwargs and not cls._flat:
            q.set_parent(kwargs["parent"])
        if "ownerid" in kwargs:
            q.owner(kwargs["ownerid"])
        if "_sortorder" in kwargs:
            for s in kwargs["_sortorder"]:
                q.add_sort(s["column"], s.get("ascending", True))
        ix = 0
        while ix < len(args):
            q.add_filter(args[ix], args[ix + 1])
            ix += 2
        return q

    @classmethod
    def create(cls, descriptor = None, parent = None, **flags):
        if descriptor is None:
            descriptor = {}
        logger.info("Creating new %s model from descriptor %s", cls.__name__, descriptor)
        kwargs = { "parent": parent }
        kwargs.update(descriptor)
        obj = cls(**kwargs)
        obj.update(descriptor)
        if hasattr(obj, "on_create") and callable(obj.on_update):
            obj.on_create(descriptor) and obj.put()
        return obj

    @classmethod
    def all(cls, **kwargs):
        cls.seal()
        return Query(cls, **kwargs)

    @classmethod
    def count(cls, **kwargs):
        cls.seal()
        return Query(cls).count()

    @classmethod
    def _import_template_data(cls, data):
        cname = cls.__name__.lower()
        if "data" in data:
            for cdata in data["data"]:
                clazz = grumble.meta.Registry.get(cdata.model)
                if clazz:
                    with gripe.pgsql.Tx.begin():
                        if clazz.all(keys_only = True).count() == 0:
                            logger.info("load_template_data(%s): Loading template model data for model %s", cname, cdata.model)
                            for d in cdata["data"]:
                                logger.debug("load_template_data(%s): model %s object %s", cname, cdata.model, d)
                                clazz.create(d)
                                
    @classmethod
    def load_template_data(cls):
        cname = cls.__name__.lower()
        fname = "data/template/" + cname + ".json"
        data = gripe.json_util.JSON.file_read(fname)
        logger.info("Importing data file %s", fname)
        if hasattr(cls, "import_template_data") and callable(cls.import_template_data):
            cls.import_template_data(data)
        else:
            cls._import_template_data(data)

def delete(model):
    if not hasattr(model, "_brandnew") and model.exists():
        if model._on_delete():
            logger.info("Deleting model %s.%s", model.kind(), model.key())
            grumble.query.ModelQuery.delete_one(model.key())
        else:
            logger.info("on_delete trigger prevented deletion of model %s.%s", model.kind(), model.key())
    return None


class Query(grumble.query.ModelQuery):
    def __init__(self, kind, keys_only = True, include_subclasses = True, **kwargs):
        super(Query, self).__init__()
        try:
            kinds = [grumble.meta.Registry.get(k) for k in kind]
        except TypeError:
            kinds = [grumble.meta.Registry.get(kind)]
        self.kind = []
        for k in kinds:
            self.kind.append(k.kind())
            if include_subclasses:
                for sub in k.subclasses():
                    self.kind.append(sub.kind())
        ancestor = kwargs.get("ancestor")
        if ancestor:
            self.set_ancestor(ancestor)
        parent = kwargs.get("parent")
        if parent:
            self.set_parent(parent)
        self.keys_only = keys_only

    def _reset_state(self):
        self._cur_kind = None
        self._results = None
        self._iter = None

    def set_ancestor(self, ancestor):
        for k in self.kind:
            if grumble.meta.Registry.get(k)._flat:
                logger.debug("Cannot do ancestor queries on flat model %s. Ignoring request to do so anyway", self.kind)
                return
        return super(Query, self).set_ancestor(ancestor)

    def set_parent(self, parent):
        for k in self.kind:
            if grumble.meta.Registry.get(k)._flat:
                logger.debug("Cannot do ancestor queries on flat model %s. Ignoring request to do so anyway", self.kind)
                return
        return super(Query, self).set_parent(parent)
    
    def get_kind(self, ix = 0):
        return grumble.meta.Registry.get(self.kind[ix]) if self.kind and ix < len(self.kind) else None

    def __iter__(self):
        self._iter = iter(self.kind)
        self._cur_kind = None
        self._results = None
        return self

    def next(self):
        ret = None
        if self._results:
            ret = next(self._results, None)
        while ret is None:
            self._cur_kind = grumble.meta.Registry.get(next(self._iter))
            self._results = iter(self.execute(self._cur_kind, self.keys_only))
            ret = next(self._results, None)
        return self._cur_kind.get(
                   grumble.key.Key(self._cur_kind, ret[self._results.key_index()]),
                   None if self.keys_only else zip(self._results.columns(), ret)
               )

    def count(self):
        ret = 0
        for k in self.kind:
            ret += self._count(k)
        return ret

    def delete(self):
        res = 0
        for k in self.kind:
            cls = grumble.meta.Registry.get(k)
            if hasattr(cls, "on_delete") and callable(cls.on_delete):
                for m in self.execute(k, self.keys_only):
                    if m.on_delete():
                        res += self.delete_one(m)
            else:
                res += self._delete(k)
        return res

    def run(self):
        return self.__iter__()

    def get(self):
        i = iter(self)
        try:
            return next(i)
        except StopIteration:
            return None

    def fetch(self):
        results = [ r for r in self ]
        ret = results[0] \
            if len(results) == 1 \
            else (results \
                    if len(results) \
                    else None)
        logger.debug("Query(%s, %s, %s).fetch(): %s", self.kind, self.filters, self._ancestor if hasattr(self, "_ancestor") else None, ret)
        return ret

