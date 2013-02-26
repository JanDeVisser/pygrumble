#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import importlib
import logging
import os.path
import re
import threading
import webapp2
from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
import gripe
import grumble
from Model import Grumble


def resolve(path):
    if path:
        (module, dot, fnc) = path.rpartition(".")
        mod = __import__(module)
        return getattr(mod, fnc) if (hasattr(mod, fnc) and callable(getattr(mod, fnc))) else None
    else:
        return None

class UserManager(object):
    def get(self, userid):
        return Grumble.User.get(userid)

    def login(self, userid, password):
        logging.debug("UserManager.login(%s, %s)", userid, password)
        return Grumble.User.login(userid, password)

    def id(self, user):
        return user.name() if user else None

    def displayname(self, user):
        return user.display_name if user else None

    def roles(self, user):
        return tuple(user.roles if user.roles else ()) if user else ()

usermanagerfactory = resolve(gripe.Config.app.get("usermanager", None)) or UserManager
usermanager = usermanagerfactory()

class SessionManager(object):
    def __init__(self):
        pass

    def _create_session(self, name = None):
        session = Grumble.HttpSession(key_name = name)
        session.put()
        return session

    def init_session(self, cookie = None):
        if not cookie:
            session = self._create_session()
        else:
            key = grumble.Key(cookie)
            session = Grumble.HttpSession.get(key)
            if not session.exists():
                session = self._create_session(key.name)
        data = session.session_data
        user = None
        if "userid" in data:
            user = usermanager.get(data["userid"])
            if not user.exists():
                user = None
        return (session.id(), data, user)

    def persist(self, session_id, data):
        session = Grumble.HttpSession.get(session_id)
        session.session_data = data
        session.put()

    def logout(self, session_id):
        session = HttpSession.get(session_id)
        grumble.delete(session)

sessionmanagerfactory = resolve(gripe.Config.app.get("sessionmanager", None)) or SessionManager
sessionmanager = sessionmanagerfactory()


class GrumbleRequestLogger(object):
    def log(self, reqctx):
        request = reqctx.request
        response = reqctx.response
        with grumble.Tx.begin():
            access = Grumble.HttpAccess()
            access.remote_addr = request.remote_addr
            access.user = reqctx.user.name() if (hasattr(reqctx, "user") and reqctx.user) else None
            access.path = request.path_qs
            access.method = request.method
            access.status = response.status
            access.put()

requestloggerfactory = resolve(gripe.Config.app.get("requestlogger", None)) or GrumbleRequestLogger
requestlogger = requestloggerfactory()

class RequestCtx(object):
    def __init__(self, request, response, defaults):
        self.request = request
        self.response = response
        for k in defaults:
            setattr(self, k, defaults[k])

class Session(object):
    _tl = threading.local()

    def __init__(self, reqctx):
        request = reqctx.request
        self.count = 0
        self._request = request
        (self._session_id, self._data, self._user) = sessionmanager.init_session(request.cookies.get("grit"))
        if self._session_id:
            request.cookies["grit"] = self._session_id
            request.response.set_cookie("grit", str(self._session_id), httponly=True)
        else:
            del request.cookies["grit"]
            request.response.delete_cookie("grit")

        request.session = self
        request.user = self._user
        reqctx.user = self._user
        reqctx.session = self
        Session._tl.session = self
        logging.debug("Session.__init__: _data: %s", self._data)

    #
    # Context Manager/pipeline entry protocol methods
    #

    @classmethod
    def begin(cls, reqctx):
        logging.debug("Session.begin")
        return Session._tl.session if hasattr(Session._tl, "session") else Session(reqctx)

    def __enter__(self):
        logging.debug("Session.__enter__")
        self.count += 1
        return self

    def __exit__(self, exception_type, exception_value, trace):
        logging.debug("Session.__exit__")
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

    def login(self, userid, password):
        logging.debug("Session.login(%s, %s)", userid, password)
        userid = usermanager.login(userid, password)
        if userid:
            self._data["userid"] = userid
        return userid

    def logout(self):
        if hasattr(request, "session"):
            del request.session
        if hasattr(request, "user"):
            del request.user
        sessionmanager.logout(self._session_id)
        del request.cookies["grit"]
        request.response.delete_cookie("grit")

    def _end(self):
        logging.debug("session._end")
        sessionmanager.persist(self._session_id, self._data)
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        if hasattr(self._tl, "session"):
            del self._tl.session

    @classmethod
    def get(cls):
        return Session._tl.session if hasattr(Session._tl, "session") else None

    def user(self):
        return self._user

    def userid(self):
        return usermanager.id(self._user)

    def roles(self):
        return usermanager.roles(self._user)

class SessionBridge(object):
    def userid(self):
        session = Session.get()
        return session.userid() if session else None

    def roles(self):
        session = Session.get()
        return session.roles() if session else None

class TxWrapper(object):
    def __init__(self, tx, request):
        if not hasattr(tx, "request"):
            tx.request = request
        self._tx = tx

    @classmethod
    def begin(cls, reqctx):
        logging.debug("TxWrapper.begin")
        return TxWrapper(grumble.Tx.begin(), reqctx.request)

    def __enter__(self):
        logging.debug("TxWrapper.__enter__")
        return self._tx.__enter__()

    def __exit__(self, exception_type, exception_value, trace):
        logging.debug("TxWrapper.__exit__(%s, %s)", exception_type, exception_value)
        return self._tx.__exit__(exception_type, exception_value, trace)

class Auth(object):
    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    def auth_needed(self):
        if not hasattr(self.reqctx, "session"):
            logging.debug("Auth.needs_auth: no session")
            return False
        if not (hasattr(self.reqctx, "roles") and self.reqctx.roles):
            logging.debug("Auth.needs_auth: no specific role needed")
            return False
        self.session = self.reqctx.session
        self.roles = self.reqctx.roles
        return True

    def logged_in(self):
        if not (hasattr(self.reqctx, "user") and self.reqctx.user):
            logging.debug("Auth.needs_login: no user. Redirecting to /login")
            self.session["redirecturl"] = self.request.path_qs
            self.response.status = "302 Moved Temporarily"
            self.response.headers["Location"] = "/login"
            return False
        else:
            self.user = self.reqctx.user
            return True

    def confirm_role(self):
        logging.debug("Auth.confirm_role(%s)", self.reqctx.roles)
        if not self.user.has_role(self.reqctx.roles):
            logging.debug("Auth.confirm_role: user %s doesn't have any role in %s", self.user.email, self.reqctx.roles)
            self.response.status = "401 Unauthorized"

    @classmethod
    def begin(cls, reqctx):
        logging.debug("Auth.begin")
        return Auth(reqctx)

    def __enter__(self):
        logging.debug("Auth.__enter__")
        self.auth_needed() and self.logged_in() and self.confirm_role()

    def __exit__(self, exception_type, exception_value, trace):
        logging.debug("Auth.__exit__(%s, %s)", exception_type, exception_value)
        return False

class Dispatcher(object):
    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    @classmethod
    def begin(cls, reqctx):
        logging.debug("Dispatcher.begin")
        return Dispatcher(reqctx)

    def __enter__(self):
        logging.debug("Dispatcher.__enter__")
        if hasattr(self.reqctx, "app"):
            logging.debug("Dispatcher.__enter__: dispatching to app %s", self.reqctx.app)
            self.reqctx.app.router.dispatch(self.request, self.response)
        elif hasattr(self.reqctx, "handler"):
            logging.debug("Dispatcher.__enter__: dispatching to handler %s", self.reqctx.handler)
            self.request.route_kwargs = {}
            h = self.reqctx.handler(self.request, self.response)
            if hasattr(h, "set_request_context") and callable(h.set_request_context):
                h.set_request_context(reqctx)
            h.dispatch()

    def __exit__(self, exception_type, exception_value, trace):
        # FIXME: Do fancy HTTP error code stuffs maybe
        logging.debug("Dispatcher.__exit__(%s, %s)", exception_type, exception_value)
        return False

class RequestLogger(object):
    """
        Pipeline entry logging requests and their results to a grumble model.
        This entry uses the __exit__ handler. It should come in the pipeline
        before (so it's __exit__ comes after) TxWrapper, so the request can be
        logged even in the case of an exception and the resulting rollback.
    """
    def __init__(self, reqctx):
        self.reqctx = reqctx
        self.request = reqctx.request
        self.response = reqctx.response

    @classmethod
    def begin(cls, reqctx):
        logging.debug("RequestLogger.begin")
        return RequestLogger(reqctx)

    def __enter__(self):
        logging.debug("RequestLogger.__enter__")

    def __exit__(self, exception_type, exception_value, trace):
        logging.debug("RequestLogger.__exit__(%s, %s)", exception_type, exception_value)
        global requestlogger
        if requestlogger:
            requestlogger.log(self.reqctx)

class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "template"
    file_suffix = "html"

    def __init__(self, request = None, response = None):
        super(ReqHandler, self).__init__(request, response)
        logging.debug("Creating request handler for %s", request.path)
        self.session = request.session if hasattr(request, "session") else None
        self.user = request.user if hasattr(request, "user") else None

    @classmethod
    def _get_env(cls):
        if not hasattr(cls, "env"):
            loader = ChoiceLoader([ \
                FileSystemLoader("%s/%s" % (gripe.root_dir(), cls.template_dir)), \
                PackageLoader("grit", "template") \
            ])
            env = Environment(loader = loader)
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
    def _get_context(self, ctx = {}, param = None):
        if not ctx:
            ctx = {}
        if param:
            ctx[param] = self.request.get(param)
        ctx['app'] = gripe.Config.app.get("about", {})
        ctx['user'] = self.user
        ctx['session'] = self.session 
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
        return ret

    def _get_content_type(self):
        if hasattr(self, "get_content_type") and callable(self.get_content_type):
            return self.get_content_type()
        elif hasattr(self, "content_type"):
            return self.content_type
        else:
            return "text/plain"

    def render(self, values = None, param = None):
        ctx = self._get_context(values, param)
        self.response.content_type = self._get_content_type()
        self.response.out.write(self._get_env().get_template(self._get_template() + "." + self.file_suffix).render(ctx))


class Login(ReqHandler):
    content_type = "text/html"

    def get(self):
        logging.debug("main::login.get")
        self.render()

    def post(self):
        logging.debug("main::login.post(%s/%s)", self.request.get("userid"), self.request.get("password"))
        url = "/"
        if "redirecturl" in self.session:
            url = self.session["redirecturl"]
            del self.session["redirecturl"]
        else:
            url = self.request.get("redirecturl", "/")
        userid = self.request.get("userid")
        password = self.request.get("password")
        assert self.session is not None, "Session missing from request handler"
        if self.session is not None and self.session.login(userid, password):
            logging.debug("Login OK")
            self.response.status = "302 Moved Temporarily"
            self.response.headers["Location"] = str(url)
        else:
            logging.debug("Login FAILED")
            self.response.status_int = 401

class Logout(ReqHandler):
    content_type = "text/html"

    def get(self):
        logging.debug("main::logout.get")
        self.request.session.logout(self.request)
        self.render()

    def post(self):
        self.get()

class StaticHandler(ReqHandler):
    def get(self, **kwargs):
        logging.debug("StaticHandler.get(%s)", self.request.path)
        path = ''
        if "abspath" in kwargs:
            path = kwargs["abspath"]
        else:
            path = gripe.root_dir()
            if "relpath" in kwargs:
                path = os.path.join(path, kwargs["relpath"])
        path += self.request.path if not kwargs.get('alias') else kwargs.get("alias")
        if not os.path.exists(path):
            logging.debug("Static file %s does not exist", path)
            self.request.response.status = "404 Not Found"
        else:
            self.response.content_length = str(os.path.getsize(path))
            self.response.content_type = gripe.get_content_type(path)
            self.response.charset = "utf-8"
            with open(path, "rb") as fh:
                self.response.text = unicode(fh.read())
                #self.response.out.write(fh.read())

class ErrorPage(ReqHandler):
    content_type = "text/html"

    def __init__(self, status, request, response, exception):
        self.status = status
        self.exception = exception
        super(ErrorPage, self).initialize(request, response)

    def get_template(self):
        return "error_%s" % self.response.status_int

    def get(self):
        logging.debug("main::ErrorPage_%s.get", self.status)
        self.render({ "request": self.request, "response": self.response})

def handle_request(request, *args, **kwargs):
    root = kwargs["root"]
    logging.debug("main::WSGIApplication::handle_request path: %s method: %s", request.path_qs, request.method)

    reqctx = RequestCtx(request, request.response, kwargs)
    def run_pipeline(l):
        logging.debug("run_pipeline(%s)", l)
        if l:
            handler_cls = l.pop(0)
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

def handle_404(request, response, exception):
    #logging.exception(exception)
    logging.info("404 for %s", request.path_qs)
    #handler = ErrorPage(404, request, response, exception)
    #handler.get()
    response.set_status(404)

class WSGIApplication(webapp2.WSGIApplication):
    def __init__(self, *args, **kwargs):
        super(WSGIApplication, self).__init__(*args, **kwargs)
        grumble.set_sessionbridge(SessionBridge())
        self.router.add(webapp2.Route("/login", handler=handle_request, defaults = { "root": self, "handler": Login, "roles": [] }))
        self.router.add(webapp2.Route("/logout", handler=handle_request, defaults = { "root": self, "handler": Logout, "roles": [] }))
        self.pipeline = []

        config = gripe.Config.app
        self.icon = config.get("icon", "/icon.png")
        self.router.add(webapp2.Route("/favicon.ico", handler=StaticHandler, defaults = { "root": self, "roles": [], "alias": self.icon }))

        container = config.get("container")
        if container:
            pipeline = container.get("pipeline")
            if pipeline:
                assert isinstance(pipeline, list), "Pipeline entry in app.container config must be list"
                for p in pipeline:
                    pipeline_class = resolve(p)
                    assert pipeline_class, "Invalid entry %s in pipeline config" % p
                    assert hasattr(pipeline_class, "begin"), "Pipeline entry %s has no 'begin' method" % p
                    self.pipeline.append(pipeline_class)
        self.pipeline.append(Dispatcher)

        for mp in config["mounts"]:
            path = "<:^%s$>" % mp["path"]
            roles = mp.get("roles", [])
            roles = [roles] if isinstance(roles, basestring) else roles
            handler = None
            defaults = { "root": self, "roles": roles }

            app_path  = mp.get("app")
            if app_path:
                (module, dot, app_obj) = app_path.rpartition(".")
                mod = importlib.import_module(module)
                assert hasattr(mod, app_obj), "Imported %s, but no object %s found" % (module, app_obj)
                wsgi_sub_app = getattr(mod, app_obj)
                assert isinstance(wsgi_sub_app, webapp2.WSGIApplication)
                handler = handle_request
                defaults["app"] = wsgi_sub_app
            else:
                handler = StaticHandler
                if "abspath" in mp:
                    defaults["abspath"] = mp["abspath"]
                if "relpath" in mp:
                    defaults["relpath"] = mp["relpath"]
            self.router.add(webapp2.Route(path, handler = handler, defaults = defaults))
        self.error_handlers[404] = handle_404

app = WSGIApplication(debug=True)

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(app, host='127.0.0.1', port='8080')
