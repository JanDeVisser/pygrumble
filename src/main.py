#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import threading
import webapp2
from jinja2 import Environment, FileSystemLoader
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
            request.response.set_cookie("grumble", self._session_id, httponly=True)
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
                request.response.headers["Location"] = where
            else:
                request.response.status_int = 401
            return request.response
    print "dispatching"
    wsgi_app.router.dispatch(request, request.response)

class SessionManagementHandler(webapp2.RequestHandler):
    @classmethod
    def get_env(cls):
        if not hasattr(cls, "env"):
            env = Environment(loader=FileSystemLoader("template"))
            cls.env = env
        return cls.env

    def _page(self, config_key, default):
        ctx = dict(grumble.Config.app.get("about", {}))
        self.response.headers['Content-Type'] = "text/html"
        self.response.out.write(self.get_env().get_template(grumble.Config.app.get(config_key, default + ".html")).render(ctx))

class Login(SessionManagementHandler):
    def get(self):
        print "main::login.get"
        self._page("loginpage", "login")

    def post(self):
        print "main::login.post %s/%s" % (self.request.get("userid"), self.request.get("password"))
        url = self.request.session.pop("redirecturl") if "redirecturl" in self.request.session else "/"
        userid = self.request.get("userid")
        password = self.request.get("password")
        if Session.login(userid, password):
            self.request.response.status = "302 Moved Temporarily"
            self.request.response.headers["Location"] = url if url else "/"
        else:
            self.request.response.status_int = 401

class Logout(SessionManagementHandler):
    def get(self):
        print "main::logout.get"
        Session.logout(self.request)
        self._page("logoutpage", "logout")

    def post(self):
        self.get()

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

app = WSGIApplication(debug=True)

if __name__ == '__main__':
#    from paste import httpserver
#    autoreload.main(httpserver.serve, (app,), {"host": '127.0.0.1', "port": '8080'})
#    httpserver.serve(app, host = '127.0.0.1', port = '8080')
    request = webapp2.Request.blank('/')
    response = request.get_response(app)
    print response
    assert response.status_int == 302, "Expected to be redirected"

    cookie = response.headers["Set-Cookie"]
    (junk,sep,cookie) = cookie.partition('"')
    (cookie,sep,junk) = cookie.partition('"')
    cookie = cookie.replace('\\075', '=')
    location  = response.headers["Location"]
    assert location == "http://localhost/login"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    response = request.get_response(app)
    print response
    assert response.status_int == 200, "Expected OK"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    request.method = "POST"
    request.POST["userid"] = "jan@de-visser.net"
    request.POST["password"] = "wbw417"
    response = request.get_response(app)
    print response
    assert response.status_int == 302, "Expected to be redirected"
    location  = response.headers["Location"]
    assert location == "http://localhost/"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    response = request.get_response(app)
    print response
    assert response.status_int == 200, "Expected OK"


