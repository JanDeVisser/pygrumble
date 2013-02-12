#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import threading
import webapp2
from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
import grumble
from Model import Grumble


def resolve(path):
    if path:
        (module, dot, handler_fnc) = path.rpartition(".")
        mod = __import__(module)
        return getattr(mod, handler_fnc) if (hasattr(mod, handler_fnc) and callable(getattr(mod, handler_fnc))) else None
    else:
        return None

class UserManager(object):
    def get(self, userid):
        return Grumble.User.get(userid)

    def login(self, userid, password):
        return Grumble.User.login(userid, password)

    def displayname(self, user):
        return user.email if user else None

usermanagerfactory = resolve(grumble.Config.app.get("usermanager", None)) or UserManager
usermanager = usermanagerfactory()

class SessionManager(object):

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

sessionmanagerfactory = resolve(grumble.Config.app.get("sessionmanager", None)) or SessionManager
sessionmanager = sessionmanagerfactory()

class Session(object):
    _tl = threading.local()

    def __init__(self, request):
        self.count = 0
        self._request = request
        (self._session_id, self._data, self._user) = sessionmanager.init_session(request.cookies.get("grumble"))
        if self._session_id:
            request.cookies["grumble"] = self._session_id
            request.response.set_cookie("grumble", str(self._session_id), httponly=True)
        else:
            del request.cookies["grumble"]
            request.response.delete_cookie("grumble")
        request.session = self._data
        request.user = self._user
        self._tl.session = self

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, exception_type, exception_value, trace):
        self.count -= 1
        if not self.count:
            self._end()
        return False

    def _login(self, userid, password):
        userid = usermanager.login(userid, password)
        if userid:
            self._data["userid"] = userid
        return userid

    @classmethod
    def login(cls, userid, password):
        if hasattr(cls._tl, "session"):
            return cls._tl.session._login(userid, password)

    def _logout(self):
        if hasattr(request, "session"):
            del request.session
        if hasattr(request, "user"):
            del request.user
        sessionmanager.logout(self._session_id)
        del request.cookies["grumble"]
        request.response.delete_cookie("grumble")

    @classmethod
    def logout(cls):
        if hasattr(cls._tl, "session"):
            return cls._tl.session.logout()

    def _end(self):
        sessionmanager.persist(self._session_id, self._data)
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        if hasattr(self._tl, "session"):
            del self._tl.session

    @classmethod
    def begin(cls, request):
        return cls._tl.session if hasattr(cls._tl, "session") else Session(request)

    @classmethod
    def get(cls, key, default = None):
        if hasattr(cls._tl, "session"):
            return cls._tl.session._data.get(key, default)

    @classmethod
    def set(cls, key, value):
        if hasattr(cls._tl, "session"):
            cls._tl.session._data[key] = value

    @classmethod
    def user(cls):
        if hasattr(cls._tl, "session"):
            return cls._tl.session._user

class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "template"
    file_suffix = "html"

    @classmethod
    def _get_env(cls):
        if not hasattr(cls, "env"):
            loader = ChoiceLoader([ \
                FileSystemLoader("%s/%s" % (grumble.root_dir(), cls.template_dir)), \
                PackageLoader("grit", "template") \
            ])
            env = Environment(loader = loader)
            if hasattr(self, "get_env") and callable(self.get_env):
                env = self.get_env(env)
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
        ctx['app'] = grumble.Config.app.get("about", {})
        ctx['user'] = self.request.user if hasattr(self.request, "user") else None
        ctx['session'] = self.request.session if hasattr(self.request, "session") else None
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
        ret = grumble.Config.app.get(cname, ret)
        return ret

    def render(self, values = None, param = None):
        ctx = self._get_context(values, param)
        self.response.headers['Content-Type'] = self.content_type
        self.response.out.write(self._get_env().get_template(self._get_template() + "." + self.file_suffix).render(ctx))


class Login(ReqHandler):
    content_type = "text/html"

    def get(self):
        print "main::login.get"
        self.render()

    def post(self):
        print "main::login.post %s/%s" % (self.request.get("userid"), self.request.get("password"))
        url = self.request.session.pop("redirecturl") if "redirecturl" in self.request.session else "/"
        userid = self.request.get("userid")
        password = self.request.get("password")
        if Session.login(userid, password):
            self.request.response.status = "302 Moved Temporarily"
            self.request.response.headers["Location"] = str(url)
        else:
            self.request.response.status_int = 401

class Logout(SessionManagementHandler):
    content_type = "text/html"

    def get(self):
        print "main::logout.get"
        Session.logout(self.request)
        self.render()

    def post(self):
        self.get()

def confirm_role(request, role):
    print "main::confirm_role(%s)" % role
    if not request.user:
        print "confirm_role: no user. Redirecting to /login"
        request.session["redirecturl"] = request.path_qs
        return "/login"
    elif not request.user.has_role(role):
        print "confirm_role: user %s doesn't have role %s" % (user.email, role)
        return 401
    else:
        print "confirm_role: OK"
        return False
    return ret

def dispatch_to_mount(request, *args, **kwargs):
    print "main::dispatch_to_mount"
    wsgi_app = kwargs["sub"]
    role = kwargs["role"]
    where = None          # FIXME UGLY MESS
    if role:
        where = confirm_role(request, role)
        if where:
            if isinstance(where, basestring):
                request.response.status = "302 Moved Temporarily"
                request.response.headers["Location"] = str(where)
            else:
                request.response.status_int = 401
            return request.response
    print "dispatching"
    wsgi_app.router.dispatch(request, request.response)


class WSGIApplication(webapp2.WSGIApplication):
    def __init__(self, *args, **kwargs):
        super(WSGIApplication, self).__init__(*args, **kwargs)
        self.router.set_dispatcher(self.__class__.custom_dispatcher)
        self.router.add(webapp2.Route("/login", handler=Login))
        self.router.add(webapp2.Route("/logout", handler=Logout))
        self.mounts = []

        config = grumble.Config.app
        for mp in config["mounts"]:
            path = mp["path"]
            app_path  = mp["app"]
            role = mp.get("role", None)
            (module, dot, app_obj) = app_path.rpartition(".")
            mod = __import__(module)
            if hasattr(mod, app_obj):
                wsgi_app = getattr(mod, app_obj)
                assert isinstance(wsgi_app, webapp2.WSGIApplication)
                self.mounts.append((path, wsgi_app))
                self.router.add(webapp2.Route(path, handler=dispatch_to_mount, defaults = { "sub": wsgi_app, "role": role }))

    @staticmethod
    def custom_dispatcher(router, request, response):
        if request.path == '/favicon.ico':
            return None
        print "main::WSGIApplication.custom_dispatcher path: %s method: %s" % (request.path_qs, request.method)

        rv = None
        user = None
        with grumble.Tx.begin():
            with Session.begin(request):
                user = usermanager.displayname(request.user) if hasattr(request, "user") else None
                rv = router.default_dispatcher(request, response)
                if not rv and request.response:
                    rv = request.response
                if isinstance(rv, basestring):
                    rv = webapp2.Response(rv)
                elif isinstance(rv, tuple):
                    rv = webapp2.Response(*rv)

        with grumble.Tx.begin():
            access = Grumble.HttpAccess()
            access.remote_addr = request.remote_addr
            access.user = user
            access.path = request.path_qs
            access.method = request.method
            access.status = rv.status
            access.put()

        return rv

