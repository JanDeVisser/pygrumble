# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$17-Sep-2013 11:30:24 AM$"

import datetime
import sys

import gripe
import gripe.pgsql
import gripe.sessionbridge
import grumble.key
import grumble.meta
import grumble.schema

logger = gripe.get_logger(__name__)

QueryType = gripe.Enum(['Columns', 'KeyName', 'Update', 'Insert', 'Delete', 'Count'])

class Sort(object):
    def __init__(self, colname, ascending):
        self.colname = colname
        self.ascending = ascending

    def order(self):
        return "ASC" if self.ascending else "DESC"

class ModelQuery(object):
    def __init__(self):
        self._owner = None
        self._filters = []
        self._sortorder = []

    def _reset_state(self):
        pass

    def set_keyname(self, keyname, kind = None):
        self._reset_state()
        assert not (self.has_parent() or self.has_ancestor()), \
            "Cannot query for ancestor or parent and keyname at the same time"
        assert ((keyname is None) or isinstance(keyname, (basestring, grumble.key.Key))), \
                "Must specify an string, Key, or None in ModelQuery.set_keyname"
        if isinstance(keyname, basestring):
            try:
                keyname = grumble.key.Key(keyname)
            except:
                keyname = grumble.key.Key(kind, keyname)
        if keyname is None:
            self.unset_keyname()
        else:
            self._keyname = keyname
        return self

    def unset_keyname(self):
        self._reset_state()
        if hasattr(self, "_keyname"):
            del self._keyname
        return self

    def has_keyname(self):
        return hasattr(self, "_keyname")

    def keyname(self):
        assert self.has_keyname(), \
            "Cannot call keyname() on ModelQuery with no keyname set"
        return self._keyname

    def set_ancestor(self, ancestor):
        self._reset_state()
        assert not (self.has_parent() or self.has_keyname()), \
            "Cannot query for ancestor and keyname or parent at the same time"
        if isinstance(ancestor, basestring):
            ancestor = grumble.key.Key(ancestor) if ancestor != "/" else None
        elif hasattr(ancestor, "key") and callable(ancestor.key):
            ancestor = ancestor.key()
        assert (ancestor is None) or isinstance(ancestor, grumble.key.Key), \
                "Must specify an ancestor object or None in ModelQuery.set_ancestor"
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
        assert not (self.has_ancestor() or self.has_keyname()), \
            "Cannot query for ancestor or keyname and parent at the same time"
        if isinstance(parent, basestring):
            ancestor = grumble.key.Key(parent) if parent != "/" else None
        elif hasattr(parent, "key") and callable(parent.key):
            parent = parent.key()
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
        return hasattr(self, "_parent")

    def parent(self):
        assert self.has_parent(), "Cannot call parent() on ModelQuery with no parent set"
        return self._parent

    def owner(self, o = None):
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
            value = value.key().name
        self._filters.append((expr, value))
        return self

    def filters(self):
        return self._filters

    def clear_sort(self):
        self._sortorder = []

    def add_sort(self, colname, ascending):
        self._reset_state()
        self._sortorder.append(Sort(colname, ascending))
        return self

    def sortorder(self):
        return self._sortorder

    def execute(self, kind, type):
        if isinstance(type, bool):
            type = QueryType.KeyName if type else QueryType.Columns
        with gripe.pgsql.Tx.begin():
            r = ModelQueryRenderer(kind, self)
            return r.execute(type)

    def _count(self, kind):
        """Executes this query and returns the number of matching rows. Note
        that the actual results of the query are not available; these need to
        be obtained by executing the query again"""
        with gripe.pgsql.Tx.begin():
            r = ModelQueryRenderer(kind, self)
            return r.execute(QueryType.Count).singleton()

    def _delete(self, kind):
        with gripe.pgsql.Tx.begin():
            r = ModelQueryRenderer(kind, self)
            return r.execute(QueryType.Delete).rowcount

    @classmethod
    def get(cls, key):
        with gripe.pgsql.Tx.begin():
            if isinstance(key, basestring):
                key = grumble.key.Key(key)
            else:
                assert isinstance(key, grumble.key.Key), "ModelQuery.get requires a valid key object"
            q = ModelQuery().set_keyname(key)
            r = ModelQueryRenderer(key.kind, q)
            return r.execute(QueryType.Columns).single_row_bycolumns()

    @classmethod
    def set(cls, insert, key, values):
        with gripe.pgsql.Tx.begin():
            if isinstance(key, basestring):
                key = grumble.key.Key(key)
            elif key is None and insert:
                pass
            elif hasattr(key, "key") and callable(key.key):
                key = key.key()
            else:
                assert isinstance(key, grumble.key.Key), "ModelQuery.get requires a valid key object, not a %s" % type(key)
            q = ModelQuery().set_keyname(key)
            r = ModelQueryRenderer(key.kind, q)
            r.execute(QueryType.Insert if insert else QueryType.Update, values)

    @classmethod
    def delete_one(cls, key):
        if isinstance(key, basestring):
            key = grumble.key.Key(key)
        elif hasattr(key, "key") and callable(key.key):
            key = key.key()
        assert isinstance(key, grumble.key.Key), "ModelQuery.delete_one requires a valid key object"
        return ModelQuery().set_keyname(key)._delete(key.kind)

class ModelQueryRenderer(object):
    def __init__(self, kind, query = None):
        self._query = query
        if isinstance(kind, grumble.schema.ModelManager):
            self._manager = kind
        else:
            kind = grumble.meta.Registry.get(kind)
            kind.seal()
            self._manager = kind.modelmanager

    def query(self, q = None):
        if q:
            self._query = q
        return self._query

    def flat(self):
        return self._manager.flat

    def audit(self):
        return self._manager.audit

    def name(self):
        return self._manager.name

    def tablename(self):
        return self._manager.tablename

    def columns(self):
        return self._manager.columns

    def key_column(self):
        return self._manager.key_col

    def has_keyname(self):
        return self._query.has_keyname()

    def keyname(self):
        return self._query.keyname()

    def has_ancestor(self):
        return self._query.has_ancestor()

    def ancestor(self):
        return self._query.ancestor()

    def has_parent(self):
        return self._query.has_parent()

    def parent(self):
        return self._query.parent()

    def owner(self):
        return self._query.owner()

    def filters(self):
        return self._query.filters()

    def sortorder(self):
        return self._query.sortorder()

    def _update_audit_info(self, new_values, insert):
        # Set update audit info:
        new_values["_updated"] = datetime.datetime.now()
        new_values["_updatedby"] = gripe.sessionbridge.get_sessionbridge().userid()
        if insert:
            # Set creation audit info:
            new_values["_created"] = new_values["_updated"]
            new_values["_createdby"] = new_values["_updatedby"]
            # If not specified, set owner to creator:
            if not new_values.get("_ownerid"):
                new_values["_ownerid"] = new_values["_createdby"]
        else:  # Update, don't clobber creation audit info:
            if "_created" in new_values:
                new_values.pop("_created")
            if "_createdby" in new_values:
                new_values.pop("_createdby")

    def _scrub_audit_info(self, new_values):
        for c in ("_updated", "_updatedby", "_created", "_createdby", "_ownerid", "_acl"):
            if c in new_values:
                del new_values[c]

    def execute(self, type, new_values = None):
        assert self._query, "Must set a Query prior to executing a ModelQueryRenderer"
        with gripe.pgsql.Tx.begin() as tx:
            key_ix = -1
            cols = ()
            vals = []
            if type == QueryType.Delete:
                sql = "DELETE FROM %s" % self.tablename()
            elif type == QueryType.Count:
                sql = "SELECT COUNT(*) AS COUNT FROM %s" % self.tablename()
                cols = ('COUNT',)
            elif type in (QueryType.Update, QueryType.Insert):
                assert new_values, "ModelQuery.execute: QueryType %s requires new values" % QueryType[type]
                if self.audit():
                    self._update_audit_info(new_values, type == QueryType.Insert)
                else:
                    self._scrub_audit_info(new_values)
                if type == QueryType.Update:
                    sql = 'UPDATE %s SET %s ' % (self.tablename(), ", ".join(['"%s" = %%s' % c for c in new_values]))
                else:  # Insert
                    sql = 'INSERT INTO %s ( "%s" ) VALUES ( %s )' % \
                            (self.tablename(), '", "'.join(new_values), ', '.join(['%s'] * len(new_values)))
                vals.extend(new_values.values())
            elif type in (QueryType.Columns, QueryType.KeyName):
                if type == QueryType.Columns:
                    cols = [c.name for c in self.columns()]
                    collist = '"' + '", "'.join(cols) + '"'
                    key_ix = cols.index(self.key_column().name)
                elif type == QueryType.KeyName:
                    cols = (self.key_column().name,)
                    collist = '"%s"' % cols[0]
                    key_ix = 0
                sql = 'SELECT %s FROM %s' % (collist, self.tablename())
            else:
                assert 0, "Huh? Unrecognized query type %s in query for table '%s'" % (type, self.name())
            if type != QueryType.Insert:
                glue = ' WHERE '
                if self.has_keyname():
                    glue = ' AND '
                    sql += ' WHERE ("%s" = %%s)' % self.key_column().name
                    vals.append(str(self.keyname().name))
                if self.has_ancestor() and self.ancestor():
                    assert not self.flat(), "Cannot perform ancestor queries on flat table '%s'" % self.name()
                    glue = ' AND '
                    sql += ' WHERE ("_ancestors" LIKE %s)'
                    vals.append(str(self.ancestor().get().path()) + "%")
                if self.has_parent():
                    assert not self.flat(), "Cannot perform parent queries on flat table '%s'" % self.name()
                    sql += glue + '("_parent" '
                    glue = ' AND '
                    if self.parent():
                        sql += " = %s"
                        vals.append(str(self.parent()))
                    else:
                        sql += " IS NULL"
                    sql += ")"
                if self.owner():
                    sql += glue + '("_ownerid" = %s)'
                    glue = ' AND '
                    vals.append(self.owner())
                for (e, v) in self.filters():
                    if v is not None:
                        sql += glue + '(%s %%s)' % e
                        vals.append(v)
                    else:
                        e = e.strip()
                        if e.endswith("!="):
                            e = e[:-2]
                            n = " IS NOT NULL"
                        elif e.endswith("="):
                            e = e[:-1]
                            n = " IS NULL"
                        else:
                            n = ""
                        sql += glue + '(%s %s)' % (e, n)
                    glue = ' AND '
            if type == QueryType.Columns and self.sortorder():
                sql += ' ORDER BY ' + ', '.join([('"' + c.colname + '" ' + c.order()) for c in self.sortorder()])
            cur = tx.get_cursor()
            cur.execute(sql, vals, columns = cols, key_index = key_ix)
            return cur

