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
import gripe.db
import grumble.key
import grumble.dbadapter

logger = gripe.get_logger(__name__)


class Sort(object):
    def __init__(self, colname, ascending=True):
        self.colname = colname
        self.ascending = ascending

    def order(self):
        return "ASC" if self.ascending else "DESC"


class Join(object):
    def __init__(self, kind, prop):
        if isinstance(kind.__class__, grumble.ModelMetaClass):
            self._kind = kind.__class__
        elif isinstance(kind, grumble.ModelMetaClass):
            self._kind = kind
        else:
            self._kind = grumble.Model.for_name(str(kind))
        self._property = prop

    def tablename(self):
        return self._kind.modelmanager.tablename()

    def columns(self):
        return self._kind.modelmanager.columns

    def key_column(self):
        return self._kind.modelmanager.key_col

    def key_column_name(self):
        return self.key_column().name


class ModelQuery(object):
    def __init__(self):
        self._owner = None
        self._limit = None
        self._filters = []
        self._sortorder = []
        self._joins = []

    def _reset_state(self):
        pass

    def set_key(self, key, kind=None):
        self._reset_state()
        assert not (self.has_parent() or self.has_ancestor()), \
            "Cannot query for ancestor or parent and key at the same time"
        assert ((key is None) or isinstance(key, (basestring, grumble.key.Key))), \
            "Must specify an string, Key, or None in ModelQuery.set_key"
        if isinstance(key, basestring):
            try:
                key = grumble.key.Key(key)
            except:
                key = grumble.key.Key(kind, key)
        if key is None:
            self.unset_key()
        else:
            self._key = key
        return self

    def unset_key(self):
        self._reset_state()
        if hasattr(self, "_key"):
            del self._key
        return self

    def has_key(self):
        return hasattr(self, "_key")

    def key(self):
        assert self.has_key(), \
            "Cannot call key() on ModelQuery with no key set"
        return self._key

    def set_ancestor(self, ancestor):
        self._reset_state()
        assert not (self.has_parent() or self.has_key()), \
            "Cannot query for ancestor and key or parent at the same time"
        if isinstance(ancestor, basestring):
            ancestor = grumble.key.Key(ancestor) if ancestor != "/" else None
        elif hasattr(ancestor, "key") and callable(ancestor.key):
            ancestor = ancestor.key()
            assert ancestor, "ModelQuery.set_ancestor: not-None ancestor with key() == None. Is the Model stored"
        assert (ancestor is None) or isinstance(ancestor, grumble.key.Key), \
            "Must specify an ancestor object or None in ModelQuery.set_ancestor"
        logger.debug("Q: Setting ancestor to %s", ancestor)
        self._ancestor = ancestor
        return self

    def unset_ancestor(self):
        self._reset_state()
        if hasattr(self, "_ancestor"):
            del self._ancestor
        return self

    def has_ancestor(self):
        return hasattr(self, "_ancestor")

    def ancestor(self):
        assert self.has_ancestor(), \
            "Cannot call ancestor() on ModelQuery with no ancestor set"
        return self._ancestor

    def set_parent(self, parent):
        self._reset_state()
        assert not (self.has_ancestor() or self.has_key()), \
            "Cannot query for ancestor or keyname and parent at the same time"
        if isinstance(parent, basestring):
            parent = grumble.key.Key(parent) if parent else None
        elif hasattr(parent, "key") and callable(parent.key):
            parent = parent.key()
            assert parent, "ModelQuery.set_parent: not-None ancestor with key() == None. Is the Model stored"
        assert (parent is None) or isinstance(parent, grumble.key.Key), \
            "Must specify a parent object or None in ModelQuery.set_parent"
        self._parent = parent
        return self

    def unset_parent(self):
        self._reset_state()
        if hasattr(self, "_parent"):
            del self._parent
        return self

    def has_parent(self):
        return hasattr(self, "_parent") or (self.has_key() and self.key() and self.key().scope())

    def parent(self):
        assert self.has_parent(), "Cannot call parent() on ModelQuery with no parent set"
        if hasattr(self, "_parent"):
            return self._parent
        else:
            return self.key().scope()

    def owner(self, o=None):
        if o is not None:
            self._reset_state()
            self._owner = o
        return self._owner

    def clear_filters(self):
        self._filters = []

    def add_filter(self, *args):
        self._reset_state()
        if len(args) == 2:
            expr = args[0]
            value = args[1]
        elif len(args) == 3:
            prop = args[0]
            assert isinstance(prop, basestring)
            prop = prop.strip()
            assert len(prop)
            prop = '"' + prop + '"' if prop[0] != '"' or prop[-1:] != '"' else prop
            expr = "%s %s" % (prop, args[1])
            value = args[2]
        else:
            assert 0, "Could not interpret %s arguments to add_filter" % len(args)
        if hasattr(value, "key") and callable(value.key):
            value = str(value.key())
        self._filters.append((expr, value))
        return self

    def add_join(self, kind, prop):
        self._joins.append(Join(kind, prop))

    def joins(self):
        return self._joins

    def filters(self):
        return self._filters

    def clear_sort(self):
        self._sortorder = []

    def add_sort(self, colname, ascending=True):
        self._reset_state()
        self._sortorder.append(Sort(colname, ascending))
        return self

    def sortorder(self):
        return self._sortorder

    def set_limit(self, limit):
        self._limit = limit
        return self

    def clear_limit(self):
        self._limit = None
        return self

    def limit(self):
        return self._limit

    def execute(self, kind, t):
        if isinstance(t, bool):
            t = grumble.dbadapter.QueryType.KeyName if t else grumble.dbadapter.QueryType.Columns
        with gripe.db.Tx.begin():
            mm = grumble.schema.ModelManager.for_name(kind)
            r = mm.getModelQueryRenderer(self)
            return r.execute(t)

    def _count(self, kind):
        """
            Executes this query and returns the number of matching rows. Note
            that the actual results of the query are not available; these need to
            be obtained by executing the query again
        """
        with gripe.db.Tx.begin():
            mm = grumble.schema.ModelManager.for_name(kind)
            r = mm.getModelQueryRenderer(self)
            return r.execute(grumble.dbadapter.QueryType.Count).singleton()

    def _delete(self, kind):
        with gripe.db.Tx.begin():
            mm = grumble.schema.ModelManager.for_name(kind)
            r = mm.getModelQueryRenderer(self)
            return r.execute(grumble.dbadapter.QueryType.Delete).rowcount

    @classmethod
    def get(cls, key):
        with gripe.db.Tx.begin():
            if isinstance(key, basestring):
                key = grumble.key.Key(key)
            else:
                assert isinstance(key, grumble.key.Key), "ModelQuery.get requires a valid key object"
            q = ModelQuery().set_key(key)
            mm = grumble.schema.ModelManager.for_name(key.kind())
            r = mm.getModelQueryRenderer(q)
            return r.execute(grumble.dbadapter.QueryType.Columns).single_row_bycolumns()

    @classmethod
    def set(cls, insert, key, values):
        with gripe.db.Tx.begin():
            if isinstance(key, basestring):
                key = grumble.key.Key(key)
            elif key is None and insert:
                pass
            elif hasattr(key, "key") and callable(key.key):
                key = key.key()
            else:
                assert isinstance(key, grumble.key.Key), \
                    "ModelQuery.get requires a valid key object, not a %s" % type(key)
            q = ModelQuery().set_key(key)
            mm = grumble.schema.ModelManager.for_name(key.kind())
            r = mm.getModelQueryRenderer(q)
            r.execute(grumble.dbadapter.QueryType.Insert if insert else grumble.dbadapter.QueryType.Update, values)

    @classmethod
    def delete_one(cls, key):
        if isinstance(key, basestring):
            key = grumble.key.Key(key)
        elif hasattr(key, "key") and callable(key.key):
            key = key.key()
        assert isinstance(key, grumble.key.Key), "ModelQuery.delete_one requires a valid key object"
        return ModelQuery().set_key(key)._delete(key.kind())
