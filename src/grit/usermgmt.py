'''
Created on 2013-03-12

@author: jan
'''

import json

import gripe
import grit

logger = gripe.get_logger("grit")

class Login(grit.ReqHandler):
    content_type = "text/html"

    def get(self):
        logger.debug("main::login.get")
        urls = {
            "reset-password": self.uri_for("reset-password"),
            "signup": self.uri_for("signup")
        }
        self.render(urls = urls)

    def post(self):
        json_request = False
        params = self.request
        if self.request.headers.get("ST-JSON-Request"):
            params = json.loads(self.request.body)
            json_request = True
        userid = params.get("userid")
        password = params.get("password")
        remember_me = params.get("remember_me", False)
        logger.debug("main::login.post(%s/%s)", userid, password)
        url = "/"
        if "redirecturl" in self.session:
            url = self.session["redirecturl"]
            del self.session["redirecturl"]
        else:
            url = self.request.get("redirecturl", "/")
        assert self.session is not None, "Session missing from request handler"
        if self.session.login(userid, password, remember_me):
            logger.debug("Login OK")
            if not json_request:
                self.response.status = "302 Moved Temporarily"
                self.response.headers["Location"] = str(url)
        else:
            logger.debug("Login FAILED")
            self.response.status_int = 401

class Logout(grit.ReqHandler):
    content_type = "text/html"

    def get_template(self):
        if gripe.Config.app and gripe.Config.app.logout and gripe.Config.app.logout.template:
            return gripe.Config.app.logout.template
        else:
            return None

    def get(self):
        logger.debug("main::logout.get")
        assert hasattr(self, "session") and self.session is not None, "Logout request handler has no session"
        self.session.logout()
        if gripe.Config.app and gripe.Config.app.logout and gripe.Config.app.logout.redirect:
            logger.debug("Logout: redirect to %s", gripe.Config.app.logout.redirect)
            self.redirect(gripe.Config.app.logout.redirect)
        else:
            urls = {
                "login": self.uri_for("login"),
                "reset-password": self.uri_for("reset-password"),
                "signup": self.uri_for("signup")
            }
            self.render(urls = urls)

    def post(self):
        self.get()

class Signup(grit.ReqHandler):
    content_type = "text/html"

    def get(self):
        logger.debug("main::SignUp.get")
        self.request.session.logout(self.request)
        urls = {
            "login": self.for_uri("login"),
            "reset-password": self.uri_for("reset-password")
        }
        self.render(urls = urls)

    def post(self):
        self.get()

class RequestPasswordReset(grit.ReqHandler):
    '''
    classdocs
    '''
    content_type = "text/html"

    def get(self):
        logger.debug("ResetPassword.get")
        self.render()

    def post(self):
        assert self.session is not None, "Session missing from request handler"
        logger.debug("ResetPassword.post(%s)", self.request.get("userid"))
        userid = self.request.get("userid")
        if userid:
            self.session.get_usermanager().reset_pwd(userid)
            self.render()
        else:
            self.error(401)


class ConfirmPasswordReset(grit.ReqHandler):
    '''
    classdocs
    '''
    content_type = "text/html"

    def post(self, code = None):
        if not code:
            code = self.request.get("code")
        if code:
            logger.debug("ConfirmReset.get(%s)", self.request.get("userid"))
            assert self.session is not None, "Session missing from request handler"
            confirm_result = self.session.get_usermanager().confirm_reset(code)
            if confirm_result == 0:
                self.error(401)
            if confirm_result == 1:
                url = self.session["redirecturl"] if "redirecturl" in self.session else "/"
                self.render(urls = { "redirecturl": url })
            elif confirm_result == 2:
                self.redirect_to("login")
            elif confirm_result == 3:
                self.redirect_to("change-password")
        else:
            self.error(401)


    def post(self):
        self.get()
