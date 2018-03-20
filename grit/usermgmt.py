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


import json
import webapp2

import gripe
import gripe.auth
import grumble
import grudge
import grit.requesthandler

logger = gripe.get_logger(__name__)


class Login(grit.requesthandler.ReqHandler):
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
        if "redirecturl" in self.session:
            url = str(self.session["redirecturl"])
            del self.session["redirecturl"]
        else:
            url = str(self.request.get("redirecturl", "/"))
        assert self.session is not None, "Session missing from request handler"
        if self.session.login(userid, password=password, remember_me=remember_me):
            logger.debug("Login OK")
            logger.debug("Sending redirect to %s", url)
            if not json_request:
                self.response.status = "302 Moved Temporarily"
                self.response.headers["Location"] = url
            else:
                self.response.headers["ST-JSON-Redirect"] = url
        else:
            logger.debug("Login FAILED")
            self.response.status_int = 401


class Logout(grit.requesthandler.ReqHandler):
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


class Profile(grit.requesthandler.ReqHandler):
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


class ChangePwd(grit.requesthandler.ReqHandler):
    def get_context(self, ctx):
        return ctx

    def get(self):
        logger.debug("usermgmt::ChangePwd.get")
        self.render()

    def post(self):
        logger.debug("usermgmt::ChangePwd.put")
        if not self.user:
            self.response.status_int = 500
            return
        json_request = False
        params = self.request
        if self.request.headers.get("ST-JSON-Request"):
            params = json.loads(self.request.body)
            json_request = True
        oldpassword = params.get("oldpassword")
        newpassword = params.get("newpassword")

        if self.user:
            if self.user.authenticate(**{"password": oldpassword}):
                self.user.changepwd(oldpassword, newpassword)
                if json_request:
                    self.json_dump({"status": "OK"})
                else:
                    self.render()
            else:
                self.response.status_int = 401
            

#
# ==========================================================================
#  S I G N U P  R E Q U E S T S
# ==========================================================================
#

@grudge.OnStarted("create_user")
@grudge.OnAdd("user_exists", grudge.Stop())
@grudge.OnAdd("user_created",
              grudge.SendMail(recipients="@.:userid",
                              subject="Confirm your registration with %s" % gripe.Config.app.about.application_name,
                              text="&signup_confirmation", status="mail_sent", context=".:prepare_message"))
@grudge.OnAdd("confirmed", "activate_user")
@grudge.OnAdd("user_activated", grudge.Stop())
@grudge.Process()
class UserSignup(grumble.Model):
    userid = grumble.TextProperty()
    password = grumble.PasswordProperty()
    display_name = grumble.TextProperty()

    user_exists = grudge.Status()
    user_created = grudge.Status()
    mail_sent = grudge.Status()
    confirmed = grudge.Status()
    user_activated = grudge.Status()

    def create_user(self):
        try:
            um = grit.Session.get_usermanager()
            um.add(self.userid, **{"password": self.password, "label": self.display_name})
            logger.debug("Create User OK")
            return self.user_created
        except gripe.auth.UserExists:
            return self.user_exists
        except gripe.Error as e:
            logger.debug("Create user Error: %s" % e)
            raise

    def prepare_message(self, msg, ctx):
        msg.set_header("X-ST-URL", "http://localhost/um/confirm/%s" % self.id())
        return ctx

    def activate_user(self):
        um = grit.Session.get_usermanager()
        try:
            user = um.get(self.userid)
            if user:
                user.confirm()
                logger.debug("Activate User OK")
                return self.user_activated
            else:
                raise gripe.auth.UserDoesntExists(self.userid)    
        except gripe.Error as e:
            logger.debug("Activate user Error: %s" % e)
            raise

#
# ==========================================================================
#  A D M I N  U S E R  C R E A T I O N
# ==========================================================================
#


@grudge.OnStarted("create_user")
@grudge.OnAdd("user_exists", grudge.Stop())
@grudge.OnAdd("user_created",
              grudge.SendMail(recipients="@.:userid",
                              subject="Confirm your registration with %s" % gripe.Config.app.about.application_name,
                              text="&confirm_creation", status="mail_sent", context=".:prepare_message"))
@grudge.OnAdd("confirmed", "activate_user")
@grudge.OnAdd("user_activated", grudge.Stop())
@grudge.Process()
class UserCreate(grumble.Model):
    userid = grumble.TextProperty()
    display_name = grumble.TextProperty()
    password = grumble.TextProperty()
    confirm = grumble.BooleanProperty()

    user_exists = grudge.Status()
    user_created = grudge.Status()
    mail_sent = grudge.Status()
    confirmed = grudge.Status()
    user_activated = grudge.Status()

    def create_user(self):
        try:
            um = grit.Session.get_usermanager()
            if not self.password:
                self.password = gripe.auth.generate_password()
            um.add(self.userid, password=self.password, display_name=self.display_name)
            self.put()
            logger.debug("Create User OK")
            return self.user_created if not self.confirm else self.confirmed
        except gripe.auth.UserExists:
            return self.user_exists
        except gripe.Error as e:
            logger.debug("Create user Error: %s" % e)
            raise

    def prepare_message(self, msg, ctx):
        msg.set_header("X-ST-URL", "%s/um/confirmreset/%s" % (Config.app.config.application_url, self.id()))
        return ctx

    def activate_user(self):
        um = grit.Session.get_usermanager()
        try:
            user = um.get(self.userid)
            if user:
                user.confirm()
                logger.debug("Activate User OK")
                return self.user_activated
            else:
                raise gripe.auth.UserDoesntExists(self.userid)    
        except gripe.Error as e:
            logger.debug("Activate user Error: %s" % e)
            raise

#
# ==========================================================================
# P A S S W O R D  R E S E T  R E Q U E S T S
# ==========================================================================
#


@grudge.OnStarted("generate_password")
@grudge.OnAdd("user_doesnt_exists", grudge.Stop())
@grudge.OnAdd("password_generated",
              grudge.SendMail(recipients="@.:userid",
                              subject="New password request for %s" % gripe.Config.app.about.application_name,
                              text="&password_reset", status="mail_sent", context=".:prepare_message"))
@grudge.OnAdd("confirmed", "reset_password")
@grudge.OnAdd("password_reset", grudge.Stop())
@grudge.Process()
class PasswordReset(grumble.Model):
    userid = grumble.TextProperty()
    password = grumble.TextProperty()

    user_doesnt_exists = grudge.Status()
    password_generated = grudge.Status()
    mail_sent = grudge.Status()
    confirmed = grudge.Status()
    password_reset = grudge.Status()

    def generate_password(self):
        try:
            logger.debug("PasswordReset::generate_password")
            um = grit.Session.get_usermanager()
            user = um.get(self.userid)
            if user is None or not user.exists():
                logger.debug("User %s does not exist", self.userid)
                return self.user_doesnt_exist
            logger.debug("User OK")
            self.password = um.gen_password()
            self.put()
            return self.password_generated
        except gripe.auth.UserExists:
            return self.user_exists
        except gripe.Error as e:
            logger.debug("Create user Error: %s" % e)
            raise

    def prepare_message(self, msg, ctx):
        msg.set_header("X-ST-URL", "%s/um/confirmreset/%s" % (Config.app.config.application_url, self.id()))
        return ctx

    def reset_password(self):
        um = grit.Session.get_usermanager()
        try:
            user = um.get(self.userid)
            if user is None:
                logger.debug("User %s does not exist", self.userid)
                return self.user_doesnt_exist
            user.password = self.password
            user.put()
            logger.debug("Password successfully reset")
            self.password = None
            self.put()
            return self.password_reset
        except gripe.Error as e:
            logger.debug("Password Reset Error: %s" % e)
            raise

app = webapp2.WSGIApplication([
        webapp2.Route(r'/login', handler=Login, name='login'),
        webapp2.Route(r'/logout', handler=Logout, name='logout'),
        webapp2.Route(r'/um/changepwd', handler=ChangePwd, name='changepwd'),

        webapp2.Route(
            r'/um/signup',
            handler="grudge.control.Startup", name='signup',
            defaults={
                "process": gripe.Config.app.workflows.signup,
                "mapping": ["userid", "password", "display_name"]
            }
        ),

        webapp2.Route(
            r'/um/confirm/<code>',
            handler="grudge.control.AddStatus", name='confirm-signup',
            defaults={
                "status": "confirmed"
            }
        ),

        webapp2.Route(
            r'/um/create',
            handler="grudge.control.Startup", name='signup',
            defaults={
                "process": gripe.Config.app.workflows.usercreate,
                "mapping": ["userid", "display_name", "password", "confirm"]
            }
        ),

        webapp2.Route(
            r'/um/confirmcreate/<code>',
            handler="grudge.control.AddStatus", name='confirm-create',
            defaults={
                "status": "confirmed"
            }
        ),

        webapp2.Route(
            r'/um/reset',
            handler="grudge.control.Startup", name='reset',
            defaults={
                "process": gripe.Config.app.workflows.pwdreset,
                "mapping": ["userid"]
            }
        ),

        webapp2.Route(
            r'/um/confirmreset/<code>',
            handler="grudge.control.AddStatus", name='confirm-reset',
            defaults={
                "status": "confirmed"
            }
        ),
    ], debug=True)
