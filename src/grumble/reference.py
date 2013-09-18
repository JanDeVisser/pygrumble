# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$17-Sep-2013 4:20:49 PM$"

import grumble.converter
import grumble.model

class ReferenceConverter(grumble.converter.PropertyConverter):
    def __init__(self, reference_class, serialize):
        self.reference_class = reference_class
        self.serialize = serialize

    def convert(self, value):
        return grumble.model.Model.get(value)

    def to_sqlvalue(self, value):
        if value is None:
            return None
        else:
            assert isinstance(value, grumble.model.Model)
            k = value.key()
            return k.name if self.reference_class else str(k)

    def from_sqlvalue(self, sqlvalue):
        return grumble.model.Model.get(
            grumble.model.Key(self.reference_class, sqlvalue) 
                if self.reference_class 
                else grumble.model.Key(sqlvalue))

    def to_jsonvalue(self, value):
        return value.to_dict() if self.serialize else value.id()

    def from_jsonvalue(self, value):
        clazz = self.reference_class
        if isinstance(value, basestring):
            value = clazz.get(value) if clazz else grumble.model.Model.get(value)
        elif isinstance(value, dict) and ("key" in value):
            value = clazz.get(value["key"])
        elif not isinstance(value, clazz):
            assert 0, "Cannot update ReferenceProperty to %s (wrong type %s)" % (value, str(type(value)))
        return value

class QueryProperty(object):
    def __init__(self, name, foreign_kind, foreign_key, private = True, serialize = False, verbose_name = None):
        self.name = name
        self.fk_kind = foreign_kind \
            if isinstance(foreign_kind, grumble.meta.ModelMetaClass) \
            else grumble.model.Model.for_name(foreign_kind)
        self.fk = foreign_key
        self.verbose_name = verbose_name if verbose_name else name
        self.serialize = serialize
        self.private = private

    def _get_query(self, instance):
        q = self.fk_kind.query()
        q.add_filter('"%s" = ' % self.fk, instance)
        return q

    def __get__(self, instance, owner):
        if not instance:
            return self
        return self._get_query(instance)

    def __set__(self, instance, value):
        raise AttributeError("Cannot set Query Property")

    def __delete__(self, instance):
        return NotImplemented

    def from_json_value(self, instance, values):
        pass

    def to_json_value(self, instance, values):
        values[self.name] = [obj.to_dict() if self.serialize else obj.id() for obj in self._get_query(instance)]

class ReferenceProperty(grumble.property.ModelProperty):
    datatype = grumble.model.Model
    sqltype = "TEXT"

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], ReferenceProperty):
            prop = args[0]
            self.reference_class = prop.reference_class
            self.collection_name = prop.collection_name
            self.collection_verbose_name = prop.collection_verbose_name
            self.serialize = prop.serialize
            self.collection_serialize = prop.collection_serialize
            self.collection_private = prop.collection_private
        else:
            self.reference_class = args[0] \
                if args \
                else kwargs.get("reference_class")
            if self.reference_class and isinstance(self.reference_class, basestring):
                self.reference_class = Model.for_name(self.reference_class)
            assert not self.reference_class or isinstance(self.reference_class, grumble.meta.ModelMetaClass)
            self.collection_name = kwargs.get("collection_name")
            self.collection_verbose_name = kwargs.get("collection_verbose_name")
            self.serialize = kwargs.get("serialize", True)
            self.collection_serialize = kwargs.get("collection_serialize", False)
            self.collection_private = kwargs.get("collection_private", True)
        self.converter = ReferenceConverter(self.reference_class, self.serialize)

    def set_kind(self, kind):
        super(ReferenceProperty, self).set_kind(kind)
        if not self.collection_name:
            self.collection_name = kind.lower() + "_set"
        if not self.collection_verbose_name:
            self.collection_verbose_name = kind.title()
        if self.reference_class:
            k = grumble.model.Model.for_name(kind)
            qp = QueryProperty(self.collection_name, k, self.name, self.collection_private, self.collection_serialize, self.collection_verbose_name)
            setattr(self.reference_class, self.collection_name, qp)
            self.reference_class._query_properties[self.collection_name] = qp

class SelfReferenceProperty(ReferenceProperty):
    def set_kind(self, kind):
        self.reference_class = grumble.model.Model.for_name(kind)
        super(SelfReferenceProperty, self).set_kind(kind)
        self.converter = ReferenceConverter(self.reference_class, self.serialize)

