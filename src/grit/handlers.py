# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$16-Nov-2012 10:01:52 PM$"

import json
import traceback
import urllib

import webapp2

import gripe
import grumble

from grit.requesthandler import ReqHandler
from grit.statichandler import StaticHandler

logger = gripe.get_logger(__name__)

class ModelBridge(object):
#    def __init__(self, kind):
#        self.kind(kind)

    def _initialize_bridge(self, key = None, kind = None):
        if kind:
            self.kind(kind)
            self.key(key or self.request.get("id", None))

    def kind(self, kind = None):
        if hasattr(self, "_kind"):
            return self._kind
        if not kind:
            assert hasattr(self, "get_kind"), "ModelBridge: kind not initialized and no get_kind method found"
            kind = self.__class__.get_kind()
            assert kind, "ModelBridge: get_kind returned 'None'"
        if not (isinstance(kind, basestring) or isinstance(kind, grumble.ModelMetaClass)):
            traceback.print_stack()
        assert isinstance(kind, basestring) or isinstance(kind, grumble.ModelMetaClass), "ModelBridge: wrong type for kind: %s" % type(kind)
        if isinstance(kind, basestring):
            self._kind = grumble.Model.for_name(kind)
            assert self._kind, "ModelBridge: unknown kind '%s'" % kind
        else:
            self._kind = kind
        return self._kind

    def get_context(self, ctx):
        return ctx

    def key(self, key = None, override = False):
        self._key = None if not hasattr(self, "_key") else self._key
        self._obj = None if not hasattr(self, "_obj") else self._obj
        if key and key.startswith("_$"):
            key = self.request.get(key[2:])
        elif self.user:
            if key == "__uid":
                key = self.user.uid()
            elif key == "__userobjid":
                key = self.user.id() if isinstance(self.user, grumble.Model) else None
        if (key and not self._key) or override:
            self._key = str(key) if key else None
            self._obj = None
        return self._key

    def object(self, key = None):
        if key:
            if isinstance(key, grumble.Model):
                self._obj = key
            else:
                self._obj = self.kind().get(key)
            self._key = self._obj.id()
        elif (not hasattr(self, "_obj") or not self._obj) and hasattr(self, "_key") and self._key:
            self._obj = self.kind().get(self._key)
        else:
            assert hasattr(self, "_obj") and self._obj, "Object not set yet"
        return self._obj

    def save(self):
        if hasattr(self, "_obj") and self._obj:
            self._obj.put()
            self._key = self._obj.id()

    def get_parent(self):
        return None

    def create(self, descriptor):
        if self.can_create():
            self._obj = self.kind().create(descriptor, self.get_parent())
            self._key = self._obj and self._obj.id()
        return self._obj

    def prepare_query(self, q):
        return q

    def query(self):
        # FIXME adapt to Model.query
        q = self._load()
        q["keys_only"] = False
        logger.info("ModelBridge::query(%s)", q)
        q = self.prepare_query(q)
        return [o for o in self.kind().query(**q)]

    def _load(self):
        pass

    def get_objects(self):
        ret = []
        if not hasattr(self, "_kind"):
            return None
        elif self.key() and self.object():
            ret = [ self.object() ]
        else:
            ret = self.query()
        ret = filter(lambda o: o.can_read(), ret)
        logger.debug("get_objects: returning %s", [ o.id() for o in ret ])
        return ret

    def can_read(self):
        return self.object().can_read()

    def can_update(self):
        return self.object().can_update()

    def can_delete(self):
        return self.object().can_delete()

    def can_create(self):
        return self.kind().can_create()

    def can_query(self):
        return self.kind().can_query()

class BridgedHandler(ModelBridge, ReqHandler):
    pass

class PageHandler(BridgedHandler):
    def get_template(self):
        prefix = self.kind().kind().replace(".", "/") + "/"
        return prefix + ("view" if self.key() else "list")

    def get_context(self, ctx):
        objs = self.get_objects()
        obj = objs[0] if objs and len(objs) else None
        ctx["key"] = self.key()
        ctx["object"] = obj
        return ctx

    def get(self, key = None, kind = None, template = None):
        self._initialize_bridge(key, kind)
        if template:
            self.template = template
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            redir = None
            if hasattr(self, "redirect_to_url") and callable(self.redirect_to_url):
                redir = self.redirect_to_url()
            if not redir:
                self.render()
            else:
                if isinstance(redir, basestring):
                    self.redirect(redir)
                else:
                    self.error(redir)
        else:
            self.error(401)

class JSHandler(BridgedHandler):
    content_type = "text/javascript"
    template_dir = "/js"
    file_suffix = "js"

    def get_context(self, ctx):
        objs = self.get_objects()
        obj = objs[0] if objs and len(objs) else None
        ctx["object"] = obj
        return ctx

    def get(self, key = None, kind = None, **kwargs):
        if "template" in kwargs:
            self.template = kwargs["template"]
        self._initialize_bridge(key, kind)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            self.render()
        else:
            self.error(401)

class PropertyBridgedHandler(BridgedHandler):
    def _initialize_bridge(self, key, kind, prop):
        super(PropertyBridgedHandler, self)._initialize_bridge(key, kind)
        logger.debug(self.kind())
        self.property(prop)

    def property(self, prop = None):
        if hasattr(self, "_prop"):
            return self._prop
        if not prop:
            if hasattr(self, "get_property"):
                prop = self.__class__.get_property()
                assert prop, "PropertyBridgedHandler: get_property returned 'None' "
        assert prop, "PropertyBridgedHandler: no property name specified"
        prop = str(prop)
        prop_obj = self.kind().properties().get(prop)
        assert prop_obj, "PropertyBridgedHandler: no property %s" % prop
        self._prop = prop
        return self._prop

class ImageHandler(PropertyBridgedHandler):
    def post(self, key = None, kind = None, prop = None):
        logger.debug("ImageHandler.post(%s.%s, %s)", kind, prop, key)
        self._initialize_bridge(key, kind, prop)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            if self.object() and self.can_update():
                setattr(self.object(), self.property(), (self.request.get("image"), self.request.get("contentType")))
                self.save()
                return self.get()
            else:
                self.error(401)
        else:
            self.error(401)

    def get(self, key = None, kind = None, prop = None):
        logger.debug("ImageHandler.get(%s.%s, %s)", kind, prop, key)
        self._initialize_bridge(key, kind, prop)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access and self.key():
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            if self.object() and self.can_read():
                if getattr(self.object(), self.property() + "_hash") in self.request.if_none_match:
                    logger.debug("Client has up-to-date image")
                    self.response.status = "304"
                else:
                    blob = getattr(self.object(), self.property());
                    assert blob, "Couldn't get contents of ImageProperty %s.%s" % (self._kind, self._prop)
                    self.response.content_type = str(blob[1])
                    self.response.etag = str(blob[2])
                    self.response.body = str(blob[0])
            else:
                self.error(404)
        else:
            self.error(401)

class JSONHandler(BridgedHandler):
    def update(self, d):
        self.object() and self.can_update() and self.object().update(d)

    def delete_obj(self):
        self.object() and self.can_delete() and grumble.delete(self.object())

    def invoke(self, d):
        assert "name" in d, "JSONHandler.invoke called without method name"
        method = d["name"]
        assert hasattr(self, method) and callable(getattr(self, method)), "%s has not method %s. Can't invoke" % (self.__class__.__name__, method)
        args = d.get("args") or []
        kwargs = d.get("kwargs") or {}
        logger.info("Invoking %s on %s using arguments *%s, **%s", method, self.__class__.__name__, args, kwargs)
        return getattr(self, method)(*args, **kwargs)

    def initialize_bridge(self):
        data = self.request.body if self.request.method == "POST" else self.request.headers.get("ST-JSON-Request")
        if data and data != '':
            data = urllib.unquote_plus(data)
            if data.endswith("="):
                (data, eq, empty) = data.rpartition("=")
            logger.debug("load() - data = %s", data)
            self._query = json.loads(data)
            if "serialization_flags" in self._query:
                self._flags = self._query["serialization_flags"]
                del self._query["serialization_flags"]
            else:
                self._flags = {}
        else:
            self._flags = {}
            self._query = {}
            
    def _load(self):
        return self._query

    def post(self, key = None, kind = None):
        logger.info("JSONHandler.post(%s,%s)\n%s", key, kind, self.request.body)
        self._initialize_bridge(key, kind)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            descriptors = self._query
            descriptors = descriptors if isinstance(descriptors, list) else [descriptors]
            ret = []
            for d in descriptors:
                if "key" in d:
                    self.key(d["key"], True)
                if "_invoke" in d and "name" in d["_method"]:
                    ret.append(self.invoke(d["_invoke"]))
                else:
                    if self.key():
                        self.update(d)
                    else:
                        self.create(d)
                    if self.object():
                        ret.append(self.object().to_dict())
            ret = ret[0] if len(ret) == 1 else ret
            self.json_dump(ret)
            return
        self.error(401)

    def get(self, key = None, kind = None):
        logger.info("JSONHandler.get(%s,%s) - JSON request: %s", key, kind, self.request.headers.get("ST-JSON-Request"))
        self._initialize_bridge(key, kind)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            objs = self.get_objects()
            ret = [o.to_dict(**self._flags) for o in objs] if objs else None
            ret = ret if ret is None or len(ret) > 1 else ret[0]
            self.json_dump(ret)
            return
        self.error(401)

    def delete(self, key = None, kind = None):
        logger.debug("JSONHandler.delete(%s, %s)", key, kind)
        self._initialize_bridge(key, kind)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            objs = self.get_objects()
            for o in objs:
                self.object(o)
                self.delete_obj()
            self.status = "204 No Content"
        else:
            self.error(401)

class RedirectHandler(BridgedHandler):
    def get(self, key = None, kind = None):
        logger.info("RedirectHandler(%s): path: %s key: %s", self.__class__.__name__, self.request.path, str(key))
        self._initialize_bridge(kind)
        has_access = True
        if hasattr(self, "allow_access") and callable(self.allow__access):
            has_access = self.allow_access()
        if has_access:
            if hasattr(self, "initialize_bridge") and callable(self.initialize_bridge):
                self.initialize_bridge()
            self.redirect(self.get_redirect_url())
        else:
            self.error(401)

app = webapp2.WSGIApplication([
        webapp2.Route(r'/json/<kind>', handler = JSONHandler, name = 'json-update'),
        webapp2.Route(r'/json/<kind>/<key>', handler = JSONHandler, name = 'json-query'),
        webapp2.Route(r'/img/<kind>/<prop>/<key>', handler = ImageHandler, name = 'image'),
    ], debug = True)

