'''
Created on 2013-03-12

@author: jan
'''

import json

import gripe
import grumble
import grudge
import grit

logger = gripe.get_logger("grit")

class Login(grit.ReqHandler):
    def get_context(self, ctx):
        return ctx

    def get_urls(self, urls):
        urls.append("reset-password", "Reset Password", None, 10)
        urls.append("signup", "Sign up", None, 20)
        return urls

    def get(self):
        logger.debug("main::login.get")
        self.render()

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
                logger.debug("Sending redirect to %s", str(url))
                self.response.status = "302 Moved Temporarily"
                self.response.headers["Location"] = str(url)
        else:
            logger.debug("Login FAILED")
            self.response.status_int = 401

class Logout(grit.ReqHandler):
    def get_template(self):
        if gripe.Config.app and gripe.Config.app.logout and gripe.Config.app.logout.template:
            return gripe.Config.app.logout.template
        else:
            return None

    def get_context(self, ctx):
        return ctx

    def get_urls(self, urls):
        urls.append("login", "Login", None, 10)
        urls.append("reset-password", "Reset Password", None, 20)
        urls.append("signup", "Sign up", None, 30)
        return urls

    def get(self):
        logger.debug("main::logout.get")
        assert hasattr(self, "session") and self.session is not None, "Logout request handler has no session"
        self.session.logout()
        if gripe.Config.app and gripe.Config.app.logout and gripe.Config.app.logout.redirect:
            logger.debug("Logout: redirect to %s", gripe.Config.app.logout.redirect)
            self.redirect(gripe.Config.app.logout.redirect)
        else:
            self.render()

    def post(self):
        self.get()

class Signup(grit.ReqHandler):
    def get_context(self, ctx):
        return ctx

    def get_urls(self, urls):
        urls.append("login", "Login", None, 10)
        urls.append("reset-password", "Reset Password", None, 20)
        urls.append("signup", "Sign up", None, 30)
        return urls

    def get(self):
        logger.debug("main::signup.get")
        self.render()

    def post(self):
        if not self.request.headers.get("ST-JSON-Request"):
            logger.debug("Non-JSON post to /signup")
            self.response.status_int = 500
        else:
            params = json.loads(self.request.body)
            userid = params.get("userid")
            password = params.get("password")
            wf = gripe.resolve(Config.app.workflows.signup)
            if wf:
                proc = wf.instantiate()
                proc.userid = userid
                proc.password = password
                proc.put()
                proc.start()
                self.render()
            else:
                logger.error("No user signup workflow defined")
                self.response_status_int = 500

@grudge.Process(entrypoint = "CreateUser")
class UserSignup(grumble.Model):
    userid = grumble.TextProperty()
    password = grumble.PasswordProperty()
    confirmation_code = grumble.TextProperty()

@OnStarted("create_user")
@OnAdd("done", Transition("../SendMail"))
@grudge.Process(parent = UserSignup)
class CreateUser(grumble.Model):
    done = Status()

    def create_user(self):
        proc = self.parent()()
        userid = proc.userid
        password = proc.password
        um = grit.Session.get_usermanager()
        try:
            confcode = um.add(userid, password)
            proc.confirmation_code = confcode
            proc.put()
            logger.debug("Create User OK")
            return self.done
        except grit.Exception as e:
            logger.debug("Create user Error: %s" % e)
            raise


@OnStarted(grudge.SendMail(recipients = "@..:userid",
    subject = "Confirm your registration with %s" % gripe.Config.app.about.application_name,
    text = "&signup_confirmation", status = "mailsent"))
@OnAdd("confirmed", Stop())
@grudge.Process(parent = UserSignup, exitpoint = True)
class SendMail(grumble.Model):
    mailsent = Status()

class RequestPasswordReset(grit.ReqHandler):
    '''
    classdocs
    '''

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

    def get(self, code = None):
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
