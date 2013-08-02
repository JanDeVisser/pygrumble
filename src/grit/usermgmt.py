'''
Created on 2013-03-12

@author: jan
'''

import json
import webapp2

import gripe
import grumble
import grudge
import grit

logger = gripe.get_logger(__name__)

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
            logger.debug("Non-JSON post to /um/signup")
            params = self.request.params
            do_json = False
        else:
            logger.debug("--> /um/signup: JSON body %s", self.request.body)
            params = json.loads(self.request.body)
            logger.debug("--> /um/signup: params %s", params)
            do_json = True
            
        userid = params.get("userid")
        password = params.get("password")
        wf = gripe.resolve(gripe.Config.app.workflows.signup)
        if wf:
            proc = wf.instantiate()
            proc.userid = userid
            proc.password = password
            proc.put()
            proc.start()
            if do_json:
                self.json_dump( { "code": proc.id() } )
            else:
                self.render()
        else:
            logger.error("No user signup workflow defined")
            self.response_status_int = 500

@grudge.OnStarted("create_user")
@grudge.OnAdd("user_created", grudge.SendMail(recipients = "@.:userid",
    subject = "Confirm your registration with %s" % gripe.Config.app.about.application_name,
    text = "&signup_confirmation", status = "mail_sent"))
@grudge.OnAdd("confirmed", "activate_user")
@grudge.OnAdd("user_activated", grudge.Stop())
@grudge.Process()
class UserSignup(grumble.Model):
    userid = grumble.TextProperty()
    password = grumble.PasswordProperty()

    user_created = grudge.Status()
    mail_sent = grudge.Status()
    confirmed = grudge.Status()
    user_activated = grudge.Status()

    def create_user(self):
        um = grit.Session.get_usermanager()
        try:
            um.add(self.userid, self.password)
            logger.debug("Create User OK")
            return self.user_created
        except gripe.Error as e:
            logger.debug("Create user Error: %s" % e)
            raise

    def activate_user(self):
        um = grit.Session.get_usermanager()
        try:
            um.confirm(self.userid)
            logger.debug("Activate User OK")
            return self.user_activated
        except gripe.Error as e:
            logger.debug("Activate user Error: %s" % e)
            raise

class ConfirmSignup(grit.ReqHandler):
    def get_template(self):
        if self._process is not None and self._process.exists() and self._process.has_status("confirmed"):
            return "confirmation_success"
        else:
            if self._process is None:
                logger.debug("get_template: _process is None")
            elif not self._process.exists():
                logger.debug("get_template: _process does not exist")
            elif not self._process.has_status("confirmed"):
                logger.debug("get_template: _process does not have status")
            return "confirm"

    def get_context(self, ctx):
        ctx["process"] = self._process
        return ctx

    def get_urls(self, urls):
        urls.append("login", "Login", None, 10)
        urls.append("reset-password", "Reset Password", None, 20)
        urls.append("signup", "Sign up", None, 30)
        return urls

    def get(self, code = None):
        logger.debug("confirm.get(%s)", code)
        logger.debug("req: %s", self.request)
        self._process = grumble.Model.get(code) if code else None
        if self._process and self._process.exists():
            logger.debug("Process exists. Setting confirmed status")
            self._process.add_status("confirmed")
        else:
            logger.debug("No process")
        self.render()

    def post(self, key = None):
        return self.get(key)


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


app = webapp2.WSGIApplication([
        webapp2.Route(r'/um/signup', handler = Signup, name = 'signup'),
        webapp2.Route(r'/um/confirm/<code>', handler = ConfirmSignup, name = 'confirm'),
        webapp2.Route(r'/login', handler = Login, name = 'login'),
        webapp2.Route(r'/logout', handler = Logout, name = 'logout'),
    ], debug = True)

#        self.router.add(webapp2.Route("/changepwd", handler = handle_request, name = "change-password",
#                                      defaults = { "root": self, "handler": "grit.usermgmt.ChangePassword", "roles": [] }))
#        self.router.add(webapp2.Route("/resetpwd", handler = handle_request, name = "reset-password",
#                                      defaults = { "root": self, "handler": "grit.usermgmt.ResetPassword", "roles": [] }))
##        self.router.add(webapp2.Route("/confirmreset", handler = handle_request, name = "confirm-reset",
#                                      defaults = { "root": self, "handler": "grit.usermgmt.ConfirmReset", "roles": [] }))

