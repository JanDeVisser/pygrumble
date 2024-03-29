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

import sys
import uuid

import gripe.acl
import gripe.db
import gripe.sessionbridge
import grumble.errors
import grumble.key
import grumble.meta
import grumble.property
import grumble.query
import grumble.schema

logger = gripe.get_logger(__name__)


class Model(object):
    __metaclass__ = grumble.meta.ModelMetaClass
    classes = {}
    acl = {"admin": "RUDQC", "owner": "RUDQ"}

    def __new__(cls, **kwargs):
        cls.seal()
        ret = super(Model, cls).__new__(cls)
        ret._brandnew = True
        ret._set_ancestors_from_parent(kwargs["parent"] if "parent" in kwargs else None)
        ret._key_name = kwargs["key_name"] \
            if "key_name" in kwargs \
            else cls.get_new_key(kwargs) if hasattr(cls, "get_new_key") and callable(cls.get_new_key) else None
        ret._acl = gripe.acl.ACL(kwargs["acl"] if "acl" in kwargs else None)
        ret._id = None
        ret._values = {}
        for (propname, prop) in ret._allproperties.items():
            setattr(ret, propname, prop._initial_value())
        for (propname, propvalue) in kwargs.items():
            if propname in ret._allproperties:
                setattr(ret, propname, propvalue)
        return ret

    @classmethod
    def schema(cls):
        cls.seal()
        ret = { "kind": cls.kind(), "flat": cls._flat, "audit": cls._audit }
        ret["properties"] = [ prop.schema() for prop in cls._properties_by_seqnr if not(prop.private) ]
        return ret

    @classmethod
    def seal(cls):
        if not hasattr(cls, "_sealed") or not (cls._sealed or hasattr(cls, "_sealing")):
            logger.info("Sealing class %s", cls.kind())
            setattr(cls, "_sealing", True)
            if cls.customizer:
                c = gripe.resolve(cls.customizer)
                if c:
                    c(cls)
            if hasattr(cls, "key_prop"):
                cls._key_propdef = getattr(cls, cls.key_prop)
                cls._key_scoped = cls._key_propdef.scoped
            else:
                cls._key_propdef = None
                cls._key_scoped = False
            cls._properties_by_seqnr = [ p for p in cls._allproperties.values() ]
            cls._properties_by_seqnr.sort(lambda p1, p2: p1.seq_nr - p2.seq_nr)
            if not cls._abstract:
                cls.modelmanager.reconcile()
            logger.info("Class %s SEALED", cls.kind())
            cls._sealed = True
            delattr(cls, "_sealing")

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
        if not(other) or not(hasattr(other, "key") and callable(other.key)):
            return False
        else:
            return self.key() == other.key()

    def __call__(self):
        return self

    def _set_ancestors_from_parent(self, parent):
        if not self._flat:
            if parent and hasattr(parent, "key") and callable(parent.key):
                parent = parent.key()
            elif isinstance(parent, basestring):
                parent = grumble.key.Key(parent)
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
                assert ancestors.endswith("/" + parent), "_set_ancestors: mismatch parent: %s, ancestors: %s" % (parent, ancestors)
                self._ancestors = ancestors
                self._parent = grumble.key.Key(parent)
        else:
            self._parent = None
            self._ancestors = "/"

    def _populate(self, values):
        if values is not None:
            self._values = {}
            self._joins = {}
            v = {k: v for (k, v) in values}
            parent = v.get("_parent")
            ancestors = v.get("_ancestors")
            self._key_name = v.get("_key_name")
            self._ownerid = v.get("_ownerid")
            self._acl = gripe.acl.ACL(v.get("_acl"))
            for prop in [p for p in self._properties.values() if not p.transient]:
                prop._update_fromsql(self, v)
            self._set_ancestors(ancestors, parent)
            if (self._key_name is None) and hasattr(self, "key_prop"):
                self._key_name = getattr(self, self.key_prop)
            self._id = self.key().id
            self._exists = True
            if hasattr(self, "after_load") and callable(self.after_load):
                self.after_load()
        else:
            self._exists = False

    def _populate_joins(self, values):
        logger.debug("_populate_joins for %s: %s", self.key(), values)
        if values is not None:
            self._joins = {k[1:]: v for (k, v) in values if k[0] == '+'}
        logger.debug("self._joins for %s: %s", self.key(), self._joins)

    def joined_value(self, join):
        if join[0] == '+':
            join = join[1:]
        logger.debug("%s.joined_value(%s) %s %s", self.key(), join,
                     join in self._joins if hasattr(self, "_joins") else "??",
                     self._joins.get(join, "???") if hasattr(self, "_joins") else "??")
        return self._joins.get(join) if hasattr(self, "_joins") else None

    def _load(self):
        # logger.debug("_load -> kind: %s, key: %s", self.kind(), str(self.key()))
        if (not(hasattr(self, "_values")) or (self._values is None)) and (self._id or self._key_name):
            self._populate(grumble.query.ModelQuery.get(self.key()))
        else:
            assert hasattr(self, "_values"), "Object of kind %s doesn't have _values" % self.kind()
            assert self._values is not None, "Object of kind %s has _values == None" % self.kind()
            assert hasattr(self, "_ancestors"), "Object of kind %s doesn't have _ancestors" % self.kind()
            assert hasattr(self, "_parent"), "Object of kind %s doesn't have _parent" % self.kind()

    def _store(self):
        self._load()
        if hasattr(self, "_brandnew"):
            for prop in self._properties.values():
                prop._on_insert(self)
            if hasattr(self, "initialize") and callable(self.initialize):
                self.initialize()
        include_key_name = not(self._key_propdef)
        if self._key_propdef:
            key = getattr(self, self.key_prop)
            if key is None:
                raise grumble.errors.KeyPropertyRequired(self.kind(), self.key_prop)
            self._key_name = key
        elif not self._key_name:
            self._key_name = uuid.uuid1().hex
        self._id = None
        self._storing = 1
        while self._storing:
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
                p = self.parent_key()
                values['_parent'] = str(p) if p else None
                values['_ancestors'] = self._ancestors
                values['_key'] = str(self.key())
            values["_acl"] = self._acl.to_json()
            values["_ownerid"] = self._ownerid if hasattr(self, "_ownerid") else None
            grumble.query.ModelQuery.set(hasattr(self, "_brandnew"), self.key(), values)
            if hasattr(self, "_brandnew"):
                if hasattr(self, "after_insert") and callable(self.after_insert):
                    self.after_insert()
                del self._brandnew
            for prop in self._properties.values():
                prop._after_store(self)
            if hasattr(self, "after_store") and callable(self.after_store):
                self.after_store()
            self._exists = True
            gripe.db.Tx.put_in_cache(self)
            self._storing -= 1
        del self._storing

    def _on_delete(self):
        return self.on_delete() if hasattr(self, "on_delete") and callable(self.on_delete) else True

    def _validate(self):
        for prop in self._properties.values():
            prop._validate(self, prop.__get__(self, None))
        if hasattr(self, "validate") and callable(self.validate):
            self.validate()

    def id(self):
        if not self._id and self._key_name:
            self._id = self.key().id
        return self._id

    def keyname(self):
        return self._key_name

    def label(self):
        return getattr(self, self.label_prop) if hasattr(self, "label_prop") else str(self)

    def parent_key(self):
        """
            Returns the parent Model of this Model, as a Key, or None if this
            Model does not have a parent.
        """
        if not(hasattr(self, "_parent")):
            self._load()
        return self._parent

    def parent(self):
        """
            Returns the parent Model of this Model, or None if this
            Model does not have a parent.
        """
        k = self.parent_key()
        return k() if k else None

    def set_parent(self, parent):
        assert not self._flat, "Cannot set parent of flat Model %s" % self.kind()
        assert str(self.key()) not in parent.path(), "Cyclical model: attempting to set %s as parent of %s" % (parent, self)
        self._load()
        self._set_ancestors_from_parent(parent)

    def ancestors(self):
        """
            Returns the ancestor path of this Model object. This is the path
            string of the parent object or empty if this object has no parent.
        """
        self._load()
        return self._ancestors if self._ancestors != "/" else ""

    def key(self):
        """
            Returns the Key object representing this Model. A Key consists of
            the Model's kind and its key name. These two identifying properties
            are combined into the Model's id, which is also part of a Key
            object.
        """
        if not self._key_name:
            return None
        else:
            return (
                grumble.key.Key(self.kind(), self.parent(), self._key_name)
                if self._key_scoped
                else grumble.key.Key(self.kind(), self._key_name))

    def path(self):
        a = self.ancestors()
        return (a if a != "/" else "") + "/" + str(self.key())

    def pathlist(self):
        """
            Returns a list containing the ancestors of this Model, the root
            Model first. If this object has no parent, the returned list is
            empty.
        """
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
        if hasattr(self, "_storing"):
            self._storing += 1
        else:
            self._store()

    def exists(self):
        if hasattr(self, "_brandnew"):
            return True
        else:
            self._load()
            return self._exists

    def to_dict(self, **flags):
        with gripe.LoopDetector.begin(self.id()) as detector:
            if detector.loop:
                logger.info("to_dict: Loop detected. %s is already serialized", self)
                return { "key": self.id() }
            p = self.parent_key()
            ret = {"key": self.id(), 'parent': p.id if p else None}
            detector.add(self.id())
            for b in self.__class__.__bases__:
                if hasattr(b, "_to_dict") and callable(b._to_dict):
                    b._to_dict(self, ret, **flags)

            def serialize(ret, (name, prop)):
                if prop.private:
                    return ret
                if hasattr(self, "to_dict_" + name) and callable(getattr(self, "to_dict_" + name)):
                    return getattr(self, "to_dict_" + name)(ret, **flags)
                else:
                    try:
                        ret[name] = prop._to_json_value(self, getattr(self, name))
                    except gripe.NotSerializableError:
                        pass
                    return ret

            ret = reduce(serialize, self._allproperties.items(), ret)
            ret = reduce(serialize, self._query_properties.items(), ret)
            hasattr(self, "sub_to_dict") and callable(self.sub_to_dict) and self.sub_to_dict(ret, **flags)
            return ret

    def _update(self, d):
        pass

    @classmethod
    def _deserialize(cls, descriptor):
        for name, prop in filter(lambda (n, p): ((not p.private) and (n in descriptor)), cls._allproperties.items()):
            value = descriptor[name]
            try:
                descriptor[name] = prop._from_json_value(value)
            except:
                logger.exception("Could not deserialize value '%s' for property '%s'", value, name)
                del descriptor[name]
        return descriptor

    def _update_deserialized(self, descriptor, **flags):
        self._load()
        try:
            for b in self.__class__.__bases__:
                if hasattr(b, "_update") and callable(b._update):
                    b._update(self, descriptor)
            for prop in filter(lambda p: not p.private and not p.readonly and (p.name in descriptor),
                               self.properties().values()):
                name = prop.name
                try:
                    value = descriptor[name]
                    if hasattr(self, "update_" + name) and callable(getattr(self, "update_" + name)):
                        getattr(self, "update_" + name)(descriptor)
                    else:
                        setattr(self, name, value)
                except:
                    raise
            self.put()
            if hasattr(self, "on_update") and callable(self.on_update):
                self.on_update(descriptor, **flags)
        except:
            logger.exception("Could not update model %s.%s using descriptor %s", self.kind(), self.keyname(), descriptor)
            raise
        return self.to_dict(**flags)

    def update(self, descriptor, **flags):
        return self._update_deserialized(self._deserialize(descriptor), **flags)

    @classmethod
    def create(cls, descriptor = None, parent = None, **flags):
        if descriptor is None:
            descriptor = {}
        try:
            kwargs = { "parent": parent }
            descriptor = cls._deserialize(descriptor)
            kwargs.update(descriptor)
            obj = cls(**kwargs)
            obj._update_deserialized(descriptor, **flags)
        except:
            logger.info("Could not create new %s model from descriptor %s", cls.__name__, descriptor)
            raise
        if hasattr(obj, "on_create") and callable(obj.on_create):
            obj.on_create(descriptor, **flags) and obj.put()
        return obj

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
        assert not cls._sealed, "Model %s is sealed. No more properties can be added" % cls.__name__
        if not hasattr(cls, propname):
            setattr(cls, propname, propdef)
        propdef.set_name(propname)
        propdef.set_kind(cls.__name__)
        mm = grumble.schema.ModelManager.for_name(cls._kind)
        if not propdef.transient:
            mm.add_column(propdef.get_coldef())
        if hasattr(propdef, "is_label") and propdef.is_label:
            # assert not hasattr(cls, "label_prop") or cls.label_prop.inherited_from, "Can only assign one label property"
            assert not propdef.transient, "Label property cannot be transient"
            cls.label_prop = propdef
        if hasattr(propdef, "is_key") and propdef.is_key:
            # assert not hasattr(cls, "key_prop") or cls.key_prop.inherited_from, "Can only assign one key property"
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
    def samekind(cls, model, sub = False):
        kinds = [cls.kind()]
        if sub:
            kinds += cls.subclasses()
        return model.kind() in kinds

    @classmethod
    def kind(cls):
        return cls._kind

    @classmethod
    def basekind(cls):
        (_, _, k) = cls.kind().rpartition(".")
        return k

    @classmethod
    def abstract(cls):
        return cls._abstract

    @classmethod
    def properties(cls):
        return cls._properties

    @classmethod
    def keyproperty(cls):
        return cls.key_prop if hasattr(cls, "key_prop") else None

    @classmethod
    def for_name(cls, name):
        return grumble.meta.Registry.get(name)

    @classmethod
    def subclasses(cls):
        return grumble.meta.Registry.subclasses(cls)

    @classmethod
    def get(cls, ident, values=None):
        k = grumble.key.Key(ident)
        if cls != Model:
            with gripe.db.Tx.begin():
                cls.seal()
                ret = None
                if hasattr(cls, "_cache") and k in cls._cache:
                    ret = cls._cache.get(k)
                    return ret
                if not ret:
                    ret = gripe.db.Tx.get_from_cache(k)
                if not ret:
                    ret = super(Model, cls).__new__(cls)
                    assert (cls.kind().endswith(k.kind())) or not k.kind(), \
                        "%s.get(%s.%s) -> wrong key kind" % (cls.kind(), k.kind(), k.name)
                    ret._id = k.id
                    ret._key_name = k.name
                    if ret._key_scoped:
                        ret._set_ancestors_from_parent(k.scope())
                    gripe.db.Tx.put_in_cache(ret)
                    if hasattr(cls, "_cache"):
                        cls._cache[ret.key()] = ret
                if values:
                    ret._populate(values)
                    ret._populate_joins(values)
        else:
            return k.modelclass().get(k, values)
        return ret

    @classmethod
    def get_by_key(cls, key):
        assert cls != Model, "Cannot use get_by_key on unconstrained Models"
        return cls.get(grumble.key.Key(cls, key))

    @classmethod
    def get_by_key_and_parent(cls, key, parent):
        cls.seal()
        assert cls != Model, "Cannot use get_by_key_and_parent on unconstrained Models"
        assert cls.key_prop, "Cannot use get_by_key_and_parent Models without explicit keys"
        q = cls.query(parent=parent)
        q.add_filter(cls.key_prop, "=", key)
        return q.get()

    @classmethod
    def by(cls, prop, value, **kwargs):
        cls.seal()
        assert cls != Model, "Cannot use by() on unconstrained Models"
        kwargs["keys_only"] = False
        q = cls.query('"%s" = ' % prop, value, **kwargs)
        return q.get()

    def children(self, cls = None):
        cls = cls or self
        q = cls.query(parent=self)
        return q

    def descendents(self, cls = None):
        cls = cls or self
        q = cls.query(ancestor=self)
        return q

    @classmethod
    def _declarative_query(cls, *args, **kwargs):
        q = Query(cls, kwargs.get("keys_only", True), kwargs.get("include_subclasses", True))
        for (k, v) in kwargs.items():
            if k == "ancestor" and not cls._flat:
                q.set_ancestor(v)
            elif k == "parent" and "ancestor" not in kwargs and not cls._flat:
                q.set_parent(v)
            elif k == "ownerid":
                q.owner(v)
            elif k == "_sortorder":
                def _add_sortorder(q, order):
                    if isinstance(order, (list, tuple)):
                        for s in order:
                            _add_sortorder(q, s)
                    elif isinstance(order, dict):
                        q.add_sort(order["column"], order.get("ascending", True))
                    else:
                        q.add_sort(str(order), True)
                _add_sortorder(q, v)
            elif isinstance(v, (list, tuple)):
                q.add_filter(k, *v)
            elif k in ("keys_only", "include_subclasses"):
                pass
            else:
                q.add_filter(k, v)
        ix = 0
        while ix < len(args):
            arg = args[ix]
            if isinstance(arg, (list, tuple)):
                q.add_filter(*arg)
                ix += 1
            else:
                assert len(args) > ix + 1
                expr = args[ix + 1]
                q.add_filter(arg, expr)
                ix += 2
        return q

    @classmethod
    def _named_search(cls, named_search, *args, **kwargs):
        factory = getattr(cls, "named_search_" + named_search)
        return factory(*args, **kwargs) \
            if factory and callable(factory) \
            else cls._declarative_query(*args, **kwargs)

    @classmethod
    def query(cls, *args, **kwargs):
        cls.seal()
        logger.debug("%s.query: args %s kwargs %s", cls.__name__, args, kwargs)
        assert cls != Model, "Cannot query on unconstrained Model class"
        named_search = kwargs.pop("named_search", None)
        return cls._named_search(named_search, *args, **kwargs) \
            if named_search \
            else cls._declarative_query(*args, **kwargs)

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
        for cdata in data:
            clazz = grumble.meta.Registry.get(cdata.model)
            if clazz:
                with gripe.db.Tx.begin():
                    if clazz.all(keys_only = True).count() == 0:
                        logger.info("_import_template_data(%s): Loading template model data for model %s", cname, cdata.model)
                        for d in cdata["data"]:
                            logger.debug("_import_template_data(%s): model %s object %s", cname, cdata.model, d)
                            clazz.create(d)

    @classmethod
    def load_template_data(cls):
        cname = cls.__name__.lower()
        dirname = cls._template_dir \
            if hasattr(cls, "_template_dir") \
            else "data/template"
        fname = "%s/%s.json" % (dirname, cname)
        data = gripe.json_util.JSON.file_read(fname)
        if data and "data" in data:
            d = data["data"]
            logger.info("Importing data file %s", fname)
            if hasattr(cls, "import_template_data") and callable(cls.import_template_data):
                cls.import_template_data(d)
            else:
                cls._import_template_data(d)


def delete(model):
    ret = 0
    if model is not None and not hasattr(model, "_brandnew") and model.exists():
        if model._on_delete():
            logger.info("Deleting model %s.%s", model.kind(), model.key())
            ret = grumble.query.ModelQuery.delete_one(model.key())
        else:
            logger.info("on_delete trigger prevented deletion of model %s.%s", model.kind(), model.key())
    return ret


def query(kind, *args, **kwargs):
    kind = grumble.meta.Registry.get(kind)
    q = kind.query(*args, **kwargs)
    return q.fetchall()


def abstract(cls):
    cls._abstract = True
    return cls


def flat(cls):
    cls._flat = True
    return cls


def unaudited(cls):
    cls._audit = False
    return cls


def cached(cls):
    cls._cache = {}
    return cls


class Query(grumble.query.ModelQuery):
    def __init__(self, kind, keys_only=True, include_subclasses=True, **kwargs):
        super(Query, self).__init__()
        self.kinds = []
        self._kindlist = []
        if isinstance(kind, basestring):
            self.kinds = [grumble.meta.Registry.get(kind)]
        else:
            try:
                self.kinds = [grumble.meta.Registry.get(k) for k in kind]
            except TypeError:
                self.kinds = [grumble.meta.Registry.get(kind)]
        self.set_includesubclasses(include_subclasses)
        self.set_keysonly(keys_only)
        if "ancestor" in kwargs:
            self.set_ancestor(kwargs["ancestor"])
        parent = kwargs.get("parent")
        if parent:
            self.set_parent(parent)

    def _reset_state(self):
        self._cur_kind = None
        self._results = None
        self._iter = None

    def set_includesubclasses(self, include_subclasses):
        self._include_subclasses = include_subclasses

    def set_keysonly(self, keys_only):
        self.keys_only = keys_only

    def set_ancestor(self, ancestor):
        for k in self.kinds:
            if grumble.meta.Registry.get(k)._flat:
                logger.debug("Cannot do ancestor queries on flat model %s. Ignoring request to do so anyway", self.kinds)
                return
        logger.debug("Q(%s): setting ancestor to %s", self.kinds, type(ancestor) if ancestor else "<None>")
        return super(Query, self).set_ancestor(ancestor)

    def set_parent(self, parent):
        for k in self.kindlist():
            if grumble.meta.Registry.get(k)._flat:
                logger.debug("Cannot do ancestor queries on flat model %s. Ignoring request to do so anyway", self.kinds)
                return
        logger.debug("Q(%s): setting parent to %s", self.kinds, parent)
        return super(Query, self).set_parent(parent)

    def get_kind(self, ix=0):
        return grumble.meta.Registry.get(self.kinds[ix]) if self.kinds and ix < len(self.kinds) else None

    def kindlist(self):
        if not self._kindlist:
            assert self.kinds
            for k in self.kinds:
                if not k.abstract():
                    self._kindlist.append(k.kind())
                if self._include_subclasses:
                    for sub in k.subclasses():
                        if not sub.abstract():
                            self._kindlist.append(sub.kind())
            assert self._kindlist
        return self._kindlist

    def __iter__(self):
        self._iter = iter(self.kindlist())
        self._cur_kind = None
        self._results = None
        if hasattr(self, "initialize_iter"):
            self.initialize_iter()
        return self

    def filter(self, model):
        return model

    def next(self):
        ret = None
        cur = None
        while ret is None:
            if self._results:
                cur = next(self._results, None)
            while cur is None:
                self._cur_kind = grumble.meta.Registry.get(next(self._iter))
                self._results = iter(self.execute(self._cur_kind, self.keys_only))
                cur = next(self._results, None)
            if cur:
                model = self._cur_kind.get(
                    grumble.key.Key(self._cur_kind, cur[self._results.key_index()]),
                    None if self.keys_only else zip(self._results.columns(), cur)
                )
                ret = self.filter(model)
        return ret

    def __len__(self):
        return self.count()

    def count(self):
        ret = 0
        for k in self.kindlist():
            ret += self._count(k)
        return ret

    def has(self):
        return self.count() > 0

    def delete(self):
        res = 0
        for k in self.kindlist():
            cls = grumble.meta.Registry.get(k)
            if hasattr(cls, "on_delete") and callable(cls.on_delete):
                for m in self:
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

    def fetchall(self):
        with gripe.db.Tx.begin():
            results = [r for r in self]
            #=======================================================================
            # ret = results[0] \
            #     if len(results) == 1 \
            #     else (results \
            #             if len(results) \
            #             else None)
            #=======================================================================
            logger.debug("Query(%s, %s, %s).fetchall(): len = %s", self.kinds, self.filters, self._ancestor
                         if hasattr(self, "_ancestor") else None, len(results))
            return results
