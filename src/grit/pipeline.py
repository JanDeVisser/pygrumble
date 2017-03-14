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


import datetime
import gripe.db
import grit

logger = gripe.get_logger(__name__)


class TxWrapper(object):
    def __init__(self, tx, request):
        if not hasattr(tx, "request"):
            tx.request = request
        self._tx = tx

    @classmethod
    def begin(cls, reqctx):
        return TxWrapper(gripe.db.Tx.begin(), reqctx.request)

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
                        grit.Session.get_usermanager(),
                        self.reqctx.roles)
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
        logger.debug("Dispatcher: Handling %s %s with body %s", self.request.method, self.request.path_qs, self.request.body)
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

