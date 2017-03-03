#
# Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#


import atexit
import datetime
import Queue
import threading
import uuid
import webapp2

import gripe
import gripe.db
import gripe.role
import gripe.sessionbridge
import grumble


import grit.log
import grit.pipeline
import grit.requesthandler
import grit.statichandler

logger = gripe.get_logger(__name__)


class Error(gripe.Error):
    pass


class UserData(grumble.Model):
    _flat = True
    _audit = False
    cookie = grumble.TextProperty(is_key = True)
    last_access = grumble.DateTimeProperty(auto_now = True)
    userid = grumble.TextProperty()
    access_token = grumble.TextProperty()
    valid_until = grumble.DateTimeProperty()


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

    def is_empty(self):
        return (len(self) == 0) and (self._user is None)

    def valid(self):
        """
            Checks if this session is still valid. A session is valid if
            it is not empty and is less than 2 hours old, or, if it is empty,
            is less than a minute old. This last condition gives users a 
            minute to login or sign up a new account.
            
            FIXME: Is that last check really necessary or can we just discard
            empty sessions at will?
            FIXME: Make time limit(s) configurable
        """
        delta = datetime.datetime.now() - self._last_access
        return ((delta.seconds < 7200) and not self.is_empty()) or \
            (delta.seconds < 60)

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
                cutoff = datetime.datetime.now() - datetime.timedelta(100)
                q = grumble.Query(UserData)
                q.add_filter("last_access <= ", cutoff)
                with gripe.db.Tx.begin():
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

    def remember_user(self, session):
        userdata = UserData()
        userdata.cookie = session.sessionid()
        userdata.userid = session.userid()
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

    def sessionid(self):
        return self.request.cookies.get("grit")


class Session(gripe.role.Guard):
    _tl = threading.local()

    _managers = {}

    def __init__(self, reqctx):
        request = reqctx.request
        self.count = 0
        self._request = request
        self._data = gripe.role.Guard.get_sessionmanager().init_session(reqctx.sessionid())
        if self._data is not None:
            self._sessionid = self._data.id()
            request.cookies["grit"] = self.sessionid()
            request.response.set_cookie("grit", self.sessionid(), httponly = True, max_age = 8640000)  # 24*3600*100 = 100 days ~ 3 months
        else:
            self.sessionid = None
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
            self.end_session()
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

    def sessiondata(self):
        return self._data

    def sessionid(self):
        return self._sessionid

    def login(self, userid, **ctx):
        password = ctx.get("password")
        remember_me = bool(ctx.get("remember_me", False))
        logger.debug("Session.login(%s, %s, %s)", userid, password, remember_me)
        user = gripe.role.Guard.get_usermanager().get(userid)
        if user:
            if user.authenticate(**ctx):
                self.user(user)
                if remember_me:
                    gripe.role.Guard.get_sessionmanager().remember_user(self)
                self.user().logged_in(self)
                return self.user()
        return None

    def logout(self):
        logger.debug("Session.logout()")
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        gripe.role.Guard.get_sessionmanager().logout(str(self._data.id()))
        del self._request.cookies["grit"]
        self._request.response.delete_cookie("grit")
        if self.user():
            self.user().logged_out(self)

    def end_session(self):
        logger.debug("Guard.end_session")
        gripe.role.Guard.get_sessionmanager().persist(self._data)
        if hasattr(self._request, "session"):
            del self._request.session
        if hasattr(self._request, "user"):
            del self._request.user
        if hasattr(Session._tl, "session"):
            del Session._tl.session

    def user(self, u = None):
        if u is not None:
            self._data.set_user(u)
        return self._data.user()

    def userid(self):
        return self.user().uid() if self.user() else None

    def roles(self):
        return self.user().roles() if self.user() else ()

    @staticmethod
    def get():
        return Session._tl.session if hasattr(Session._tl, "session") else None


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

def handle_request(request, *args, **kwargs):
    """
        Handles a request to a grit application by feeding it through the 
        pipeline set up in the application config. The final element of the
        pipeline is typically the Dispatcher, which dispatches the request either
        to a sub-application or a request handler. Other pipeline elements
        are
            . TxWrapper, which initializes the database transaction in which the
              request runs,
            . Auth, which ensures that the requesting user has appropriate
              permissions to execute the request
            . Session, which associates a Session object with the request.
            
        Pipeline entries use the 'with' protocol, with the added extension that
        the 'begin' method is assumed to act as a factory for the element, i.e.
        the pattern is
        
          with pipeline_element_class.begin(reqctx):
                ...
                
        The 'begin' classmethod should return a pipeline element, initialized 
        with the request context object which holds a reference to the request
        and response objects. The 'with' protocol will then call the __enter__
        and __exit__ methods. The elements are stacked, which means that first
        all the __enter__ methods will be called, end then all the __exit__
        methods, but in reverse order. Also, when any begin() or __enter__
        method sets the response's status to an error-like number (>= 300), the 
        rest of the pipeline is skipped. The __exit__ methods of the entries
        whose __enter__ methods were executed are still executed in that case.
    """
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


class WSGIApplication(webapp2.WSGIApplication):
    def __init__(self, *args, **kwargs):
        self.apps = {}
        super(WSGIApplication, self).__init__(*args, **kwargs)
        gripe.sessionbridge.set_sessionbridge(SessionBridge())
        self.pipeline = []

        config = gripe.Config.app
        self.icon = config.get("icon", "/icon.png")
        logger.info("Application icon: %s", self.icon)
        self.router.add(webapp2.Route("/favicon.ico", handler = grit.statichandler.StaticHandler, defaults = { "root": self, "roles": [], "alias": self.icon }))

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
        self.pipeline.append(grit.pipeline.Dispatcher)

        for mp in config["mounts"]:
            raw_path = mp.get("path")
            app_path = mp.get("app")
            assert raw_path, "Must specify a path for each mount in app.conf"
            path = "<:^%s$>" % raw_path
            roles = mp.get("roles", [])
            roles = roles.split() if isinstance(roles, basestring) else roles
            defaults = { "root": self, "roles": roles }

            if app_path:
                logger.debug("WSGIApplication(): Mounting app %s at path %s", app_path, raw_path)
                wsgi_sub_app = gripe.resolve(app_path, None)
                assert wsgi_sub_app, "WSGI app %s not found" % app_path
                defaults["app"] = app_path
                logger.info("WSGIApplication(): Adding handler app %s for path %s", app_path, raw_path)
            elif "abspath" in mp or "relpath" in mp:
                logger.debug("WSGIApplication(): Redirecting %s to StaticHandler", raw_path)
                defaults["handler"] = grit.statichandler.StaticHandler
                if "abspath" in mp:
                    defaults["abspath"] = mp["abspath"]
                if "relpath" in mp:
                    defaults["relpath"] = mp["relpath"]
            else:
                logger.debug("WSGIApplication(): mount for path %s ignored", raw_path)
                continue
            self.router.add(webapp2.Route(path, handler = handle_request, defaults = defaults))
        self.error_handlers[404] = grit.requesthandler.handle_404


app = WSGIApplication(debug = True)

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(app, host = '127.0.0.1', port = '8080')
