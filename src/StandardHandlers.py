import threading
# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$16-Nov-2012 10:01:52 PM$"

import json
import logging
import webapp2

from jinja2 import Environment, FileSystemLoader

from Model import Grumble
import Util

class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "/template"
    file_suffix = "html"
    env = None

    def get_session(self, key):
        return Grumble.Session.get_session()

    @classmethod
    def get_env(cls):
        if not cls.env:
            env = Environment(loader=FileSystemLoader(Util.get_path(cls.template_dir)))
            env.filters['formatdistance'] = Util.format_distance
            env.filters['datetime'] = Util.format_datetime
            env.filters['prettytime'] = Util.prettytime
            env.filters['avgspeed'] = Util.avgspeed
            env.filters['speed'] = Util.speed
            env.filters['pace'] = Util.pace
            env.filters['avgpace'] = Util.avgpace
            env.filters['weight'] = Util.weight
            env.filters['height'] = Util.height
            env.filters['length'] = Util.length
            cls.env = env
        return cls.env

    def get_context(self, ctx):
        return ctx

    def _get_context(self, ctx = {}, param = None):
        if not ctx:
            ctx = {}
        if param:
            ctx[param] = self.request.get(param)
        ctx['user'] = users.get_current_user()
        ctx['units'] = Util.units
        ctx['units_table'] = Util.units_table
        ctx['url'] = users.create_logout_url(self.request.uri) \
            if users.get_current_user() \
            else None
        ctx['tab'] = self.request.get('tab', None)
        logging.info("--> _get_context: %s", str(ctx))
        ctx = self.get_context(ctx)
        logging.info("--> after get_context: %s", str(ctx))
        return ctx

    def _get_template(self):
        ret = self.template \
            if hasattr(self, "template") \
            else None
        if not ret:
            ret = self.get_template() \
                if hasattr(self, "get_template") and callable(self.get_template) \
                else None
        if not ret:
            ret = self.get_modelclass().__name__.lower() \
                if hasattr(self, "get_modelclass") and callable(self.get_modelclass) \
                else None
        return ret

    def render(self, template, values = None, param = None):
        ctx = self._get_context(values, param)
        self.response.headers['Content-Type'] = self.content_type
        logging.info("Rendering '%s.%s'", template, self.file_suffix)
        self.response.out.write(self.get_env().get_template(template + "." + self.file_suffix).render(ctx))

class BridgedHandler(ReqHandler):
    def allow_access(self):
        return users.get_current_user()

    def must_redirect_to(self):
        return users.create_login_url(self.request.uri) if not self.allow_access() else None

    def user_can_update(self, obj):
        return True

    def user_can_query(self, obj):
        return True

    def user_can_create(self):
        return True

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
                if obj and not(self.user_can_query(obj)):
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
            self.render(self._get_template(), { "object": obj } if obj else {})
        else:
            self.error(401)

class ImageHandler(BridgedHandler):
    def post(self):
        key = self.request.get("id", None)
	if self.allow_access() and key:
            self.initialize_bridge(self.request)
            obj = self.get_object(key)
            if obj and self.user_can_update(obj):
                obj.set_image(self.request.get("contentType"), self.request.get("image"))
                return self.get(key)
            else:
                self.error(401)
        else:
            self.error(401)

    def get(self, key):
        logging.info("ImageHandler(%s): path: %s key: %s", self.__class__.__name__, self.request.path, str(key))
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

