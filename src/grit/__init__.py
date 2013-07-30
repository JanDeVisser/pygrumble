#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import atexit
import datetime
import hashlib
import importlib
import jinja2
import json
import logging
import os.path
import Queue
import re
import threading
import uuid
import webapp2
import sys


import gripe
import gripe.json_util
import gripe.pgsql
import gripe.url
import grumble

logger = gripe.get_logger(__name__)

class Error(gripe.Error):
    pass

import gripe.role
import gripe.auth
import grit.log

class UserData(grumble.Model):
    _flat = True
    _audit = False
    cookie = grumble.TextProperty(is_key = True)
    last_access = grumble.DateTimeProperty(auto_now = True)
    userid = grumble.TextProperty()


class SessionData(dict):
    def __init__(self, id):
        self._id = id if id else uuid.uuid1().hex
        self._user = None
        self.touch()

    def id(self):
        return self._id

    def __str__(self):
        return self.id()

    def __repr__(self):
        return self.id()

    def touch(self):
        self._last_access = datetime.datetime.now()

    def valid(self):
        delta = datetime.datetime.now() - self._last_access
        return (((delta.seconds < 7200) and (len(self) > 0)) or
                    (delta.seconds < 60))

    def set_user(self, user):
        self._user = user

    def user(self):
        return self._user

class SessionManager(object):
    _singleton = None

    def __init__(self):
        assert SessionManager._singleton is None, "SessionManager is a singleton"
        SessionManager._singleton = self
        self._sessions = {}
        self._queue = Queue.Queue()
        self._lock = threading.RLock()
        self._thread = threading.Thread(target = SessionManager._monitor)
        self._thread.setDaemon(True)
        atexit.register(SessionManager._exiting)
        self._lastharvest = None
        self._thread.start()

    @staticmethod
    def _monitor():
        SessionManager._singleton._monitor_()

    def _monitor_(self):
        try:
            return self._queue.get(timeout = 5.0)
        except:
            pass
        while True:
            with self._lock:
                for (id, session) in self._sessions.items():
                    if not session.valid():
                        logger.debug("Session %s not valid anymore. Weeding", id)
                        del self._sessions[id]

            delta = datetime.datetime.now() - self._lastharvest if self._lastharvest else None
            if (not delta) or (delta.days > 0):
                logger.info("Weeding UserData")
                mm = UserData.modelmanager
                cutoff = datetime.datetime.now() - datetime.timedelta(100)
                q = grumble.Query(UserData)
                q.add_filter("last_access <= ", cutoff)
                with gripe.pgsql.Tx.begin():
                    result = q.delete()
                    logger.info("Weeded %s cookies", result)
                    self._lastharvest = datetime.datetime.now()
            try:
                return self._queue.get(timeout = 1.0)
            except:
                pass

    @staticmethod
    def _exiting():
        SessionManager._singleton._exiting_()

    def _exiting_(self):
        try:
            self._queue.put(True)
            if self._db is not None:
                with self._dblock:
                    self._db.close()
        except:
            pass
        self._thread.join()

    def _get_session(self, cookie):
        session = None
        with self._lock:
            if cookie:
                logger.debug("Sessions: %s", self._sessions)
                session = self._sessions.get(cookie)
            if session is None:
                logger.info("No session for cookie %s. Creating", cookie if cookie else "[None]")
                session = SessionData(cookie)
                if not cookie:
                    logger.info("New session cookie %s", session.id())
                self._sessions[session.id()] = session
            else:
                logger.info("Found session with id %s", session.id())
                session.touch()
                logger.info("Existing session found. User %s", session.user())
            return session

    def _get_user(self, cookie):
        ret = None
        if cookie:
            logger.debug("Looking up cookie %s in UserData", cookie)
            userdata = UserData.get_by_key(cookie)
            if userdata and userdata.exists():
                ret = Session.get_usermanager().get(userdata.userid) if userdata.userid else None
                logger.debug("Found cookie in UserData. Userid %s", ret)
                userdata.last_access = datetime.datetime.now()
                userdata.put()
            else:
                logger.debug("Cookie not found in UserData")
        return ret

    def init_session(self, cookie = None):
        session = self._get_session(cookie)
        if not session.user():
            session.set_user(self._get_user(cookie))
        return session

    def remember_user(self, cookie, uid):
        userdata = UserData()
        userdata.cookie = cookie
        userdata.userid = uid
        userdata.last_access = datetime.datetime.now()
        userdata.put()

    def persist(self, data):
        with self._lock:
            self._sessions[data.id()] = data

    def logout(self, cookie):
        cookie = str(cookie)
        userdata = UserData.get_by_key(cookie)
        if userdata:
            grumble.delete(userdata)
        with self._lock:
            if cookie in self._sessions:
                del self._sessions[cookie]

class RequestCtx(object):
    def __init__(self, request, response, defaults):
        self._created = datetime.datetime.now()
        self.request = request
        self.response = response
        for k in defaults:
            setattr(self, k, defaults[k])

class Session(object):
    _tl = threading.local()

    _managers = {}

    @classmethod
    def _get_manager(cls, manager, default):
        if manager not in Session._managers:
            Session._managers[manager] = gripe.Config.resolve("app.%smanager" % manager, default)()
        return Session._managers[manager]

    @classmethod
    def get_usermanager(cls):
        return Session._get_manager("user", "grit.auth.UserManager")

    @classmethod
    def get_rolemanager(cls):
        return Session._get_manager("role", "grit.role.RoleManager")

    @classmethod
    def get_sessionmanager(cls):
        return Session._get_manager("session", "grit.SessionManager")

    def __init__(self, reqctx):
        request = reqctx.request
        self.count = 0
        self._request = request
        self._data = Session.get_sessionmanager().init_session(request.cookies.get("grit"))
        if self._data is not None:
            request.cookies["grit"] = self._data.id()
            request.response.set_cookie("grit", self._data.id(), httponly = True, max_age = 8640000)  # 24*3600*100 = 100 days ~ 3 months
        else:
            del request.cookies["grit"]
            request.response.delete_cookie("grit")

        request.session = self
        reqctx.session = self
        Session._tl.session = self
        logger.debug("Session.__init__: _data: %s", self._data)

    #
    # Context Manager/pipeline entry protocol methods
    #

    @classmethod
    def begin(cls, reqctx):
        return Session._tl.session if hasattr(Session._tl, "session") else Session(reqctx)

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, exception_type, exception_value, trace):
        self.count -= 1
        if not self.count:
            self._end()
        return False

    #
    # dict-like protocol methods
    #

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return self._data.__iter__()

    def __contains__(self, item):
        return item in self._data

    def login(self, userid, password, remember_me = False):
        logger.debug("Session.login(%s, %s, %s)", userid, password, remember_me)
        user = Session.get_usermanager().login(userid, password)
        if user:
            self._data.set_user(user)
            self._user = user
            if remember_me:
                Session.get_sessionmanager().remember_user(self._data.id(), userid)
        return user

    def logout(self):
        logger.debug("Session.logout()")
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        Session.get_sessionmanager().logout(str(self._data.id()))
        del self._request.cookies["grit"]
        self._request.response.delete_cookie("grit")

    def _end(self):
        logger.debug("session._end")
        Session.get_sessionmanager().persist(self._data)
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        if hasattr(Session._tl, "session"):
            del Session._tl.session

    @staticmethod
    def get():
        return Session._tl.session if hasattr(Session._tl, "session") else None

    def user(self):
        return self._data.user()

    def userid(self):
        return self.user().uid() if self.user() else None

    def roles(self):
        return self.user().roles() if self.user() else ()

class SessionBridge(object):
    """
        Bridge between a grit session and the sessions required by grumble.
        Grumble only uses a userid and roles for authorization and audit
        purposes. The grit WSGIApplication instantiates this class and
        sets the instance as the bridge between the grit session associated with
        the running thread and grumble.
    """
    def userid(self):
        session = Session.get()
        return session.userid() if session is not None else None

    def roles(self):
        session = Session.get()
        return session.roles() if session is not None else None

class TxWrapper(object):
    def __init__(self, tx, request):
        if not hasattr(tx, "request"):
            tx.request = request
        self._tx = tx

    @classmethod
    def begin(cls, reqctx):
        return TxWrapper(gripe.pgsql.Tx.begin(), reqctx.request)

    def __enter__(self):
        return self._tx.__enter__()

    def __exit__(self, exception_type, exception_value, trace):
        return self._tx.__exit__(exception_type, exception_value, trace)

class Auth(object):
    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    def auth_needed(self):
        if not hasattr(self.reqctx, "session"):
            logger.debug("Auth.needs_auth: no session")
            return False
        self.session = self.reqctx.session
        if self.session.user():
            self.request.user = self.session.user()
            self.reqctx.user = self.session.user()
        if not (hasattr(self.reqctx, "roles") and self.reqctx.roles):
            logger.debug("Auth.needs_auth: no specific role needed")
            return False
        self.roles = self.reqctx.roles
        return True

    def logged_in(self):
        if self.session.user():
            logger.debug("Auth.logged_in: User present: %s", self.session.userid())
            return True
        logger.debug("Auth.logged_in: no user. Redirecting to /login")
        self.session["redirecturl"] = self.request.path_qs
        self.response.status = "302 Moved Temporarily"
        self.response.headers["Location"] = "/login"
        return False

    def confirm_role(self):
        logger.debug("Auth.confirm_role(%s)", self.reqctx.roles)
        if not self.session.user().has_role(self.reqctx.roles):
            logger.warn("Auth.confirm_role: user %s doesn't have any role in %s",
                        Session.get_usermanager().id(self.user), self.reqctx.roles)
            self.response.status = "401 Unauthorized"

    @classmethod
    def begin(cls, reqctx):
        return Auth(reqctx)

    def __enter__(self):
        self.auth_needed() and self.logged_in() and self.confirm_role()
        return self

    def __exit__(self, exception_type, exception_value, trace):
        return False

class Dispatcher(object):
    apps = {}

    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    @classmethod
    def begin(cls, reqctx):
        return Dispatcher(reqctx)

    def __enter__(self):
        if hasattr(self.reqctx, "app"):
            app_path = self.reqctx.app
            logger.info("Dispatcher: dispatching to app %s", app_path)
            app = self.apps.get(app_path)
            if not app:
                app = gripe.resolve(app_path, None)
                assert app, "WSGI app %s not found" % app_path
                self.apps[app_path] = app
            app.router.dispatch(self.request, self.response)
        elif hasattr(self.reqctx, "handler"):
            handler = self.reqctx.handler
            if isinstance(handler, basestring):
                h = gripe.resolve(handler, None)
                assert h, "WSGI handler %s not found" % handler
                handler = h
            logger.info("Dispatcher: dispatching to handler %s", handler)
            self.request.route_kwargs = {}
            h = handler(self.request, self.response)
            if hasattr(h, "set_request_context") and callable(h.set_request_context):
                h.set_request_context(self.reqctx)
            h.dispatch()
        return self

    def __exit__(self, exception_type, exception_value, trace):
        # TODO: Do fancy HTTP error code stuffs maybe
        return False

class RequestLogger(object):
    """
        Pipeline entry logger requests and their results to a grumble model.
        This entry uses the __exit__ handler. It should come in the pipeline
        before (so it's __exit__ comes after) TxWrapper, so the request can be
        logged even in the case of an exception and the resulting rollback.
    """

    _requestlogger = None

    @classmethod
    def get_requestlogger(cls):
        if cls._requestlogger is None:
            cls._requestlogger = gripe.Config.resolve("app.requestlogger", "grit.log.HttpAccessLogger")()
        return cls._requestlogger

    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    @classmethod
    def begin(cls, reqctx):
        return RequestLogger(reqctx)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, trace):
        self.reqctx.time_elapsed = datetime.datetime.now() - self.reqctx._created
        if RequestLogger.get_requestlogger():
            logger.debug("Logging request")
            RequestLogger.get_requestlogger().log(self.reqctx)
        return False

class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "template"
    file_suffix = "html"

    def __init__(self, request = None, response = None):
        super(ReqHandler, self).__init__(request, response)
        logger.info("Creating request handler for %s", request.path)
        self.session = request.session if hasattr(request, "session") else None
        self.user = request.user if hasattr(request, "user") else None
        self.errors = []

    @classmethod
    def _get_env(cls):
        if not hasattr(cls, "env"):
            loader = jinja2.ChoiceLoader([ \
                jinja2.FileSystemLoader("%s/%s" % (gripe.root_dir(), cls.template_dir)), \
                jinja2.PackageLoader("grit", "template") \
            ])
            env = jinja2.Environment(loader = loader)
            if hasattr(cls, "get_env") and callable(cls.get_env):
                env = cls.get_env(env)
            cls.env = env
        return cls.env

# Move to --sweattrails specific mixin
#    @classmethod
#    def get_env(cls, env):
#        env.filters['formatdistance'] = Util.format_distance
#        env.filters['datetime'] = Util.format_datetime
#        env.filters['prettytime'] = Util.prettytime
#        env.filters['avgspeed'] = Util.avgspeed
#        env.filters['speed'] = Util.speed
#        env.filters['pace'] = Util.pace
#        env.filters['avgpace'] = Util.avgpace
#        env.filters['weight'] = Util.weight
#        env.filters['height'] = Util.height
#        env.filters['length'] = Util.length
#        return env

# Move to sweattrails specific mixin
#    def get_context(self, ctx):
#        ctx['units'] = Util.units
#        ctx['units_table'] = Util.units_table
#        ctx['tab'] = self.request.get('tab', None)
#        return ctx
#
    def add_error(self, error):
        self.errors.append(error)

    def _get_context(self, ctx = None):
        logger.debug("_get_context %s", ctx)
        if ctx is None:
            logger.debug("_get_context: ctx is None. Building new one")
            ctx = {}
        ctx['app'] = gripe.Config.app.get("about", {})
        ctx['user'] = self.user
        ctx['session'] = self.session
        ctx['params'] = self.request.params
        ctx['errors'] = self.errors
        urls = ctx.get("urls")
        if urls is None:
            logger.debug("_get_context: urls is None. Building new collection")
            urls = gripe.url.UrlCollection("root")
        else:
            logger.debug("_get_context: urls already present in context")
        assert urls is not None, "Hrm. urls is still None"
        urls.uri_factory(self)
        if self.user is not None and hasattr(self.user, "urls"):
            urls.copy(self.user.urls())
        if hasattr(self, "urls"):
            urls.copy(self.user.urls())
        ctx["urls"] = urls
        if hasattr(self, "get_context") and callable(self.get_context):
            ctx = self.get_context(ctx)
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
            ret = self.get_kind().__name__.lower() \
                if hasattr(self, "get_kind") and callable(self.get_kind) \
                else None
        cname = self.__class__.__name__.lower()
        if not ret:
            ret = cname
        ret = gripe.Config.app.get(cname, ret)
        logger.info("ReqHandler: using template %s", ret)
        return ret

    def _get_content_type(self):
        if hasattr(self, "get_content_type") and callable(self.get_content_type):
            return self.get_content_type()
        elif hasattr(self, "content_type"):
            return self.content_type
        else:
            content_type = gripe.ContentType.for_path(self.request.path)
            return content_type.content_type if content_type else "text/plain"

    def json_dump(self, obj):
        if obj:
            logging.info("retstr=%s", json.dumps(obj))
            self.response.content_type = "application/json"
            self.response.json = obj
        else:
            self.status = "204 No Content"

    def render(self):
        ctx = self._get_context()
        self.response.content_type = self._get_content_type()
        self.response.out.write(self._get_env().get_template(self._get_template() + "." + self.file_suffix).render(ctx))


class StaticHandler(ReqHandler):
    etags = {}

    def get(self, **kwargs):
        logger.info("StaticHandler.get(%s)", self.request.path)
        path = ''
        if "abspath" in kwargs:
            path = kwargs["abspath"]
        else:
            path = gripe.root_dir()
            if "relpath" in kwargs:
                path = os.path.join(path, kwargs["relpath"])
        path += self.request.path if not kwargs.get('alias') else kwargs.get("alias")
        if not os.path.exists(path):
            logger.info("Static file %s does not exist", path)
            self.request.response.status = "404 Not Found"
        else:
            if_none_match = self.request.if_none_match
            hashvalue = self.etags.get(path)
            if if_none_match and hashvalue and hashvalue in if_none_match:
                logger.debug("Client has up-to-date resource %s", path)
                self.response.status = "304 Not Modified"
            else:
                self.response.content_length = str(os.path.getsize(path))
                content_type = gripe.ContentType.for_path(path)
                self.response.content_type = content_type.content_type
                if content_type.is_text():
                    self.response.charset = "utf-8"
                    mode = "r"
                else:
                    mode = "rb"
                with open(path, mode) as fh:
                    buf = fh.read()
                if path not in self.etags:
                    hashvalue = hashlib.md5(buf).hexdigest()
                    self.etags[path] = hashvalue
                    if if_none_match and hashvalue in if_none_match:
                        logger.debug("Client has up-to-date resource %s. I had to hash it though", path)
                        self.response.status = "304 Not Modified"
                        return
                self.response.etag = hashvalue
                self.response.body = str(buf)

class ErrorPage(ReqHandler):
    content_type = "text/html"

    def __init__(self, status, request, response, exception):
        self.status = status
        self.exception = exception
        super(ErrorPage, self).initialize(request, response)

    def get_template(self):
        return "error_%s" % self.response.status_int

    def get(self):
        logger.info("main::ErrorPage_%s.get", self.status)
        self.render({ "request": self.request, "response": self.response})

def handle_request(request, *args, **kwargs):
    root = kwargs["root"]
    logger.info("WSGIApplication::handle_request path: %s method: %s", request.path_qs, request.method)

    reqctx = RequestCtx(request, request.response, kwargs)
    def run_pipeline(l):
        if l:
            handler_cls = l.pop(0)
            logger.debug("running pipeline entry %s", handler_cls)
            with handler_cls.begin(reqctx):
                if 0 <= reqctx.response.status_int <= 299:
                    run_pipeline(l)

    run_pipeline(list(root.pipeline))

    rv = request.response
    if isinstance(rv, basestring):
        rv = webapp2.Response(rv)
    elif isinstance(rv, tuple):
        rv = webapp2.Response(*rv)
    request.response = rv
    logger.debug("Pipeline completed with response status %s", rv.status)

def handle_404(request, response, exception):
    # logger.exception(exception)
    logger.info("404 for %s", request.path_qs)
    # handler = ErrorPage(404, request, response, exception)
    # handler.get()
    response.set_status(404)

class WSGIApplication(webapp2.WSGIApplication):
    def __init__(self, *args, **kwargs):
        self.apps = {}
        super(WSGIApplication, self).__init__(*args, **kwargs)
        grumble.set_sessionbridge(SessionBridge())
        self.pipeline = []

        config = gripe.Config.app
        self.icon = config.get("icon", "/icon.png")
        logger.info("Application icon: %s", self.icon)
        self.router.add(webapp2.Route("/favicon.ico", handler = StaticHandler, defaults = { "root": self, "roles": [], "alias": self.icon }))

        container = config.get("container")
        if container:
            pipeline = container.get("pipeline")
            if pipeline:
                assert isinstance(pipeline, list), "Pipeline entry in app.container config must be list"
                for p in pipeline:
                    logger.info("Adding pipeline entry %s", p)
                    pipeline_class = gripe.resolve(p)
                    assert pipeline_class, "Invalid entry %s in pipeline config" % p
                    assert hasattr(pipeline_class, "begin"), "Pipeline entry %s has no 'begin' method" % p
                    self.pipeline.append(pipeline_class)
        self.pipeline.append(Dispatcher)

        for mp in config["mounts"]:
            raw_path = mp.get("path")
            assert raw_path, "Must specify a path for each mount in app.conf"
            path = "<:^%s$>" % raw_path
            roles = mp.get("roles", [])
            roles = [roles] if isinstance(roles, basestring) else roles
            handler = None
            defaults = { "root": self, "roles": roles }

            app_path = mp.get("app")
            if app_path:
                wsgi_sub_app = gripe.resolve(app_path, None)
                assert wsgi_sub_app, "WSGI app %s not found" % app_path
                handler = handle_request
                defaults["app"] = app_path
                logger.info("WSGIApplication(): Adding handler app %s for path %s", app_path, raw_path)
            else:
                handler = StaticHandler
                if "abspath" in mp:
                    defaults["abspath"] = mp["abspath"]
                if "relpath" in mp:
                    defaults["relpath"] = mp["relpath"]
                logger.info("WSGIApplication(): Adding static handler for path %s", raw_path)
            self.router.add(webapp2.Route(path, handler = handler, defaults = defaults))
        self.error_handlers[404] = handle_404


app = WSGIApplication(debug = True)

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(app, host = '127.0.0.1', port = '8080')
