import threading
# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$16-Nov-2012 10:01:52 PM$"

import json
import logging
import webapp2

from jinja2 import Environment, FileSystemLoader

import grit
import grumble
from Model import Grumble
import Util


class ModelBridge(object):
    def _initialize(self, kind = None):
        if hasattr(self, "_kind"):
            return
        if not kind:
            assert hasattr(self, "get_kind"), "ModelBridge: No get_kind in bridge class '%s'" % self.__class__.__name__
            kind = self.__class__.get_kind()
            assert kind, "ModelBridge: get_kind returned 'None' "
        if isinstance(kind, basestring):
            self._kind = grumble.Model.for_name(kind)
            assert self._kind, "ModelBridge: unknown kind '%s'" % kind
        elif isinstance(kind, grumble.ModelMetaClass):
            self._kind = kind
        else:
            assert 0, "ModelBridge.initialize called with invalid kind '%s' of type '%s'" % (kind, type(kind))

    def kind(self):
        _initialize()
        return self._kind

    def get_context(self, ctx):
        return ctx

    def get_object(self, key):
        return self.kind().get(key)

    def save_object(self, obj):
        if obj:
            obj.put()

    def get_parent(self):
        return None

    def create_object(self, descriptor):
        return self.kind().create(descriptor, self.get_parent())

    def prepare_query(self, q):
        return q

    def query(self, q):
        print "query(%s)" % q
        q = self.prepare_query(q)
        objs = self.kind().query(q)
        return [ obj.to_dict() for obj in objs ]

    def can_read(self, obj):
        return obj.can_read()

    def can_update(self, obj):
        return obj.can_update()

    def can_delete(self, obj):
        return obj.can_delete()

    def can_create(self):
        return self.kind().can_create()

    def can_query(self):
        return self.kind().can_query()


class BridgedHandler(grit.ReqHandler):
    def allow_access(self):
        return True

    def must_redirect_to(self):
        return None

    def call_initialize_bridge(self):
        hasattr(self, "initialize_bridge") and callable(self.initialize_bridge) and self.initialize_bridge()

class JSHandler(BridgedHandler):
    content_type = "text/javascript"
    template_dir = "/js"
    file_suffix = "js"

    def get(self, key = None):
	if self.allow_access():
            self.call_initialize_bridge()
            key = key or self.request.get("id", None)
            obj = None
            if key:
                obj = self.get_object(key)
                if obj and not(self.can_read(obj)):
                    obj = None
            else:
                objs = None
                body = self.request.body
                if body and body != '':
                    logging.info("query=%s", body)
                    q = json.loads(body)
                    objs = self.query(q)
                if objs:
                    obj = objs[0]
            self.render({ "object": obj } if obj else {})
        else:
            self.error(401)

class ImageHandler(BridgedHandler):
    def __init__(self, kind = None, prop = None):
        self.kind = kind
        self.prop = prop

    def post(self, kind = None, prop = None):
        kind = kind or self.kind
        assert kind, "ImageHandler: Model kind must be specified either in __init__ or application route"
        kind_cls = grumble.Model.for_name(kind)
        assert kind_cls, "ImageHandler: Unknown model kind %s" % kind
        prop = prop or self.prop
        assert prop, "ImageHandler: Model property must be specified either in __init__ or application route"
        prop_obj = kind_cls.properties()[prop]
        assert prop_obj,  "ImageHandler: Kind %s does not have property %s" % (kind, prop)
        assert isinstance(prop_obj, ImageProperty), "ImageHandler: %s.%s is not an image property" % (kind, prop)
        key = self.request.get("id", None)
	if self.allow_access() and key:
            self.call_initialize_bridge()
            obj = self.get_object(key)
            if obj and self.can_update(obj):
                setattr(obj, prop, (self.request.get("image"), self.request.get("contentType")))
                self.save_obj(obj)
                return self.get(key, kind, prop)
            else:
                self.error(401)
        else:
            self.error(401)

    def get(self, key, kind = None, prop = None):
        kind = kind or self.kind
        assert kind, "ImageHandler: Model kind must be specified either in __init__ or application route"
        kind_cls = grumble.Model.for_name(kind)
        assert kind_cls, "ImageHandler: Unknown model kind %s" % kind
        prop = prop or self.prop
        assert prop, "ImageHandler: Model property must be specified either in __init__ or application route"
        prop_obj = kind_cls.properties()[prop]
        assert prop_obj,  "ImageHandler: Kind %s does not have property %s" % (kind, prop)
        assert isinstance(prop_obj, ImageProperty), "ImageHandler: %s.%s is not an image property" % (kind, prop)
        key = key or self.request.get("id", None)
	if self.allow_access() and key:
            logging.info("ImageHandler(%s): going with key: %s", self.__class__.__name__, key)
            self.call_initialize_bridge()
            obj = self.get_object(key)
            logging.info("ImageHandler(%s): name: %s", self.__class__.__name__, obj and obj.name or "None")
            if obj and self.user_can_query(obj):
                blob = obj.get_image()
                if blob:
                    self.response.headers['Content-Type'] = str(blob[0])
                    self.response.out.write(blob[1])
                else:
                    self.error(404)
            else:
                self.error(404)
        else:
            self.error(401)

class JSONHandler(BridgedHandler):
    def update_object(self, obj, d):
        obj.update(d)

    def post(self):
	if self.allow_access():
            self.call_initialize_bridge()
            logging.info("data=%s", self.request.body)
            d = json.loads(self.request.body)
            if "key" in d:
                obj = self.get_object(d["key"])
                if obj and self.user_can_update(obj):
                    self.update_object(obj, d)
                else:
                    obj = None
            elif self.user_can_create():
                obj = self.create_object(d)
            if obj:
                return self.get(str(obj.key()))
        self.error(401)

    def get(self, key = None):
	if self.allow_access():
            self.call_initialize_bridge()
            key = key or self.request.get("id", None)
            if key:
                obj = self.get_object(key)
                ret = obj.to_dict() if obj and self.user_can_query(obj) else None
            else:
                body = self.request.body
                q = {}
                if body and body != '':
                    logging.info("query=%s", body)
                    q = json.loads(body)
                ret = self.query(q)
            if ret is not None:
                retstr = json.dumps(ret)
                logging.info("retstr=%s", retstr)
                self.response.out.write(retstr)
                return
            else:
                logging.info("ret is None")
        self.error(401)

    def delete(self):
	if self.allow_access():
            self.call_initialize_bridge()
            logging.info("query=%s", self.request.body)
            q = json.loads(self.request.body)
            if "key" in q:
                obj = self.get_object(q["key"])
                if obj and self.user_can_delete(obj):
                    hasattr(obj, "on_delete") and callable(obj.on_delete) and obj.on_delete(q)
                    if hasattr(obj, "remove") and callable(obj.remove):
                        obj.remove(q)
                    else:
                        obj.delete()
        else:
            self.error(401)

class PageHandler(BridgedHandler, ReqHandler):
    def get(self, key = None):
        redir = self.must_redirect_to()
	if not redir:
            self.call_initialize_bridge()
            key = key or self.request.get("id", None)
            obj = None
            if key:
                obj = self.get_object(key)
                if obj and not(self.user_can_query(obj)):
                    obj = None
            else:
                body = self.request.body
                objs = None
                if body and body != '':
                    logging.info("query=%s", body)
                    q = json.loads(body)
                    objs = self.query(q)
                if objs:
                    obj = objs[0]

            self.render(self._get_template(), { obj.__class__.__name__.lower(): obj } if obj else {})
        else:
            if isinstance(redir, str):
                self.redirect(redir)
            else:
                self.error(redir)

class RedirectHandler(BridgedHandler):
    def get(self, key):
        logging.info("RedirectHandler(%s): path: %s key: %s", self.__class__.__name__, self.request.path, str(key))
        key = key or self.request.get("id", None)
	if self.allow_access() and key:
            self.call_initialize_bridge()
            self.redirect(self.get_redirect_url(self.get_object(key)))
        else:
            self.error(401)

