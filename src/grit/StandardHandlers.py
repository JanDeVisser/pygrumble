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
from Model import Grumble
import Util

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

