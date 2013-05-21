'''
Created on 2013-04-23

@author: jan
'''

import operator
import gripe

logger = gripe.get_logger("gripe")

class UrlCollectionElem(object):

    def _initialize(self, ident, label, level):
        self._ident = self._label = self._level = None
        self._collection = None
        self._ident = ident
        self.label(label)
        self.level(level)

    def ident(self):
        return self._ident

    def label(self, l = None):
        if l is not None:
            self._label = str(l)
        return self._label if self._label else self.ident()

    def level(self, lvl = None):
        if lvl is not None:
            self._level = int(lvl)
        return self._level

    def collection(self, c = None):
        if c is not None:
            assert isinstance(c, UrlCollection), "UrlCollectionElem.collection argument must be UrlCollection"
            self._collection = c
        return self._collection


class Url(UrlCollectionElem):
    def __init__(self, *args):
        self._url = None
        if len(args) == 1:
            if isinstance(args[0], dict):
                d = args[0]
                self._initialize(d.get("id"), d.get("label"), d.get("level"))
                self.url(d.get("url"))
            elif isinstance(args[0], Url):
                u = args[0]
                self._initialize(u.ident(), u.label(), u.level())
                self.url(u.url())
            elif isinstance(args[0], basestring):
                self._initialize(args[0], None, 10)
            else:
                assert 0, "Cannot initialize Url with this argument: %s" % args[0]
        else:
            assert 1 < len(args) < 4, "Cannot initialize Url with these args: %s" % args
            self._initialize(args[0], args[1] if len(args) > 1 else None, int(args[3]) if (len(args) > 3) and args[3] else 10)
            self.url(args[2] if len(args) > 2 else None)

    def url(self, u = None):
        if u is not None:
            self._url = u
        if self._url is None and self.collection() is not None:
            self._url = self.collection().uri_for(self.ident())
            assert self._url is not None, "No url found for id %s" % self.ident()
        return self._url

    def __repr__(self):
        return '<url id="%s" href="%s" level="%s">%s</url>' % (self.ident(), self.url(), self.level(), self.label())

class UrlCollection(UrlCollectionElem, dict):
    def __init__(self, *args):
        self._factory = None
        if len(args) == 1:
            if isinstance(args[0], UrlCollection):
                c = args[0]
                self._initialize(c.ident(), c.label(), c.level())
                self.copy(c)
            elif isinstance(args[0], dict):
                d = args[0]
                self._initialize(d.get("id"), d.get("label"), d.get("level"))
                self.append(d.get("urls"))
            elif isinstance(args[0], basestring):
                self._initialize(args[0], None, 10)
            else:
                assert 0, "Cannot initialize UrlCategory with %s <%s>" % (args[0], type(args[0]))
        else:
            assert len(args) > 1, "Cannot initialize UrlCategory with these arguments: %s" % args
            self._initialize(args[0], args[1], int(args[2]) if (len(args) > 2) and args[2] else 10)
            if (len(args) > 3) and args[3]:
                self.append(*args[3:])

    def copy(self, other):
        for u in other.urls():
            self.append(Url(u))
        for c in other.collections():
            self.append(UrlCollection(c))        
    
    def append(self, *urls):
        for u in urls:
            if isinstance(u, (list, tuple)):
                self.append(*u)
            elif isinstance(u, UrlCollection):
                c = self.get(u.ident())
                if c is not None and isinstance(c, UrlCollection):
                    c.append(u.urls())
                else:
                    c = u
                    self[c.ident()] = c
                c.collection(self)
            elif u is not None:
                u = Url(u)
                u.collection(self)
                self[u.ident()] = u

    def urls(self):
        return sorted([url for url in self.values() if isinstance(url, Url)], key = operator.attrgetter("_level", "_ident"))

    def collections(self):
        return sorted([c for c in self.values() if isinstance(c, UrlCollection)], key = operator.attrgetter("_level", "_ident"))

    def elements(self):
        return sorted(self.values(), key = operator.attrgetter("_level", "_ident"))

    def uri_factory(self, factory = None):
        if factory is not None:
            self._factory = factory
        return self._factory if self._factory or (self.collection() is None) else self.collection().uri_factory()

    def uri_for(self, ident):
        f = self.uri_factory()
        return f.uri_for(ident) if f is not None else None

    def __repr__(self):
        return '<collection id="%s" label="%s" level="%s">%s</collection>' % (self.ident(), self.label(), self.level(), "".join([str(e) for e in self.elements()]))

