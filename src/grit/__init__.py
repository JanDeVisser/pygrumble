#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import logging
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
        return user.id() if user else None

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

class RequestCtx(object):
    def __init__(self, router, request, response):
        self.router = router
        self.request = request
        self.response = response

class Session(object):
    _tl = threading.local()

    def __init__(self, reqctx):
        request = reqctx.request
        self.count = 0
        self._request = request
        (self._session_id, self._data, self._user) = sessionmanager.init_session(request.cookies.get("grumble"))
        if self._session_id:
            request.cookies["grumble"] = self._session_id
            request.response.set_cookie("grumble", str(self._session_id), httponly=True)
        else:
            del request.cookies["grumble"]
            request.response.delete_cookie("grumble")

        request.session = self
        request.user = self._user
        reqctx.user = self._user
        self._tl.session = self
        logging.debug("Session.__init__: %s, %s", self.__class__._tl, threading.current_thread().ident)

    #
    # Context Manager/pipeline entry protocol methods
    #

    @classmethod
    def begin(cls, reqctx):
        logging.debug("Session.begin")
        return cls._tl.session if hasattr(cls._tl, "session") else Session(reqctx)

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
        del request.cookies["grumble"]
        request.response.delete_cookie("grumble")

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
        return cls._tl.session if hasattr(cls._tl, "session") else None

    def user(self):
        return self._user

    def userid(self):
        return usermanager.id(self._user)

    def roles(self):
        return usermanager.roles(self._user)


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
        rv = self.reqctx.router.default_dispatcher(self.request, self.response)
        if not rv and self.request.response:
            rv = self.request.response
        if isinstance(rv, basestring):
            rv = webapp2.Response(rv)
        elif isinstance(rv, tuple):
            rv = webapp2.Response(*rv)
        self.reqctx.response = rv

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
        with grumble.Tx.begin():
            access = Grumble.HttpAccess()
            access.remote_addr = self.request.remote_addr
            access.user = self.reqctx.user if hasattr(self.reqctx, "user") else None
            access.path = self.request.path_qs
            access.method = self.request.method
            access.status = self.response.status
            access.put()

class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "template"
    file_suffix = "html"

    def __init__(self, request = None, response = None):
        super(ReqHandler, self).__init__(request, response)
        logging.debug("Creating request handler for %s", request.path)
        self.session = request.session if hasattr(request, "session") else None
        assert self.session is not None, "ReqHandler.session is None"
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

# Move to sweattrails specific mixin
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
            ret = self.get_modelclass().__name__.lower() \
                if hasattr(self, "get_modelclass") and callable(self.get_modelclass) \
                else None
        cname = self.__class__.__name__.lower()
        if not ret:
            ret = cname
        ret = gripe.Config.app.get(cname, ret)
        return ret

    def render(self, values = None, param = None):
        ctx = self._get_context(values, param)
        self.response.headers['Content-Type'] = self.content_type
        self.response.out.write(self._get_env().get_template(self._get_template() + "." + self.file_suffix).render(ctx))


class Login(ReqHandler):
    content_type = "text/html"

    def get(self):
        logging.debug("main::login.get")
        self.render()

    def post(self):
        logging.debug("main::login.post(%s/%s)", self.request.get("userid"), self.request.get("password"))
        url = self.session["redirecturl"] if "redirecturl" in self.session else "/"
        del self.request.session["redirecturl"]
        userid = self.request.get("userid")
        password = self.request.get("password")
        assert self.session is not None, "Session missing from request handler"
        if self.session is not None and self.request.session.login(userid, password):
            logging.debug("Login OK")
            self.request.response.status = "302 Moved Temporarily"
            self.request.response.headers["Location"] = str(url)
        else:
            logging.debug("Login FAILED")
            self.request.response.status_int = 401

class Logout(ReqHandler):
    content_type = "text/html"

    def get(self):
        logging.debug("main::logout.get")
        self.request.session.logout(self.request)
        self.render()

    def post(self):
        self.get()

def confirm_role(request, role):
    logging.debug("main::confirm_role(%s)", role)
    if not request.user:
        logging.debug("confirm_role: no user. Redirecting to /login")
        request.session["redirecturl"] = request.path_qs
        return "/login"
    elif not request.user.has_role(roles):
        logging.debug("confirm_role: user %s doesn't have any role in %s", user.email, roles)
        return 401
    else:
        logging.debug("confirm_role: OK")
        return False
    return ret

def dispatch_to_mount(request, *args, **kwargs):
    logging.debug("main::dispatch_to_mount")
    wsgi_app = kwargs["app"]
    roles = kwargs["roles"]
    where = None          # FIXME UGLY MESS
    if roles:
        where = confirm_role(request, roles)
        if where:
            if isinstance(where, basestring):
                request.response.status = "302 Moved Temporarily"
                request.response.headers["Location"] = str(where)
            else:
                request.response.status_int = 401
            return request.response
    logging.debug("dispatching")
    wsgi_app.router.dispatch(request, request.response)

class WSGIApplication(webapp2.WSGIApplication):
    _app = None

    def __init__(self, *args, **kwargs):
        assert self.__class__._app is None, "grit.WSGIApplication is a singleton"
        self.__class__._app = self
        super(WSGIApplication, self).__init__(*args, **kwargs)
        self.router.set_dispatcher(self.__class__.custom_dispatcher)
        self.router.add(webapp2.Route("/login", handler=Login))
        self.router.add(webapp2.Route("/logout", handler=Logout))
        self.mounts = []
        self.pipeline = []

        config = gripe.Config.app
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
            path = mp["path"]
            app_path  = mp["app"]
            roles = mp.get("roles", [])
            roles = [roles] if isinstance(roles, basestring) else roles
            (module, dot, app_obj) = app_path.rpartition(".")
            mod = __import__(module)
            if hasattr(mod, app_obj):
                wsgi_sub_app = getattr(mod, app_obj)
                assert isinstance(wsgi_sub_app, webapp2.WSGIApplication)
                self.mounts.append((path, wsgi_sub_app))
                self.router.add(webapp2.Route(path, handler=dispatch_to_mount, defaults = { "root": self, "app": wsgi_sub_app, "roles": roles }))

    @staticmethod
    def custom_dispatcher(router, request, response):
        if request.path == '/favicon.ico':
            return None
        logging.debug("main::WSGIApplication.custom_dispatcher path: %s method: %s", request.path_qs, request.method)

        reqctx = RequestCtx(router, request, response)
        def run_pipeline(l):
            logging.debug("run_pipeline(%s)", l)
            if l:
                handler_cls = l.pop(0)
                with handler_cls.begin(reqctx):
                    run_pipeline(l)

        run_pipeline(list(WSGIApplication._app.pipeline))
        return reqctx.response

if __name__ == '__main__':
    app = WSGIApplication(debug=True)
    from paste import httpserver
    httpserver.serve(app, host='127.0.0.1', port='8080')
