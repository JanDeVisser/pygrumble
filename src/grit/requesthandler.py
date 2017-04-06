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

import jinja2
import webapp2

import gripe
import gripe.url

logger = gripe.get_logger(__name__)


class ReqHandler(webapp2.RequestHandler):
    content_type = "application/xhtml+xml"
    template_dir = "template"
    file_suffix = "html.j2"

    def __init__(self, request=None, response=None):
        super(ReqHandler, self).__init__(request, response)
        logger.info("Creating request handler for %s", request.path)
        self.session = request.session if hasattr(request, "session") else None
        self.user = request.user if hasattr(request, "user") else None
        self.errors = []

    @classmethod
    def _get_env(cls):
        if not hasattr(cls, "env"):
            loader = jinja2.ChoiceLoader([
                jinja2.FileSystemLoader("%s/%s" % (gripe.root_dir(), cls.template_dir)),
                jinja2.PackageLoader("grit", "template")
            ])
            env = jinja2.Environment(loader=loader, extensions=['jinja2.ext.do'])
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
    def add_error(self, error):
        self.errors.append(error)

    def _get_context(self, ctx=None):
        logger.debug("_get_context %s", ctx)
        if ctx is None:
            logger.debug("_get_context: ctx is None. Building new one")
            ctx = {}
        ctx['app'] = gripe.Config.app.get("about", {})
        ctx['config'] = gripe.Config.app.get("config", {})
        ctx['user'] = self.user
        ctx['session'] = self.session
        ctx['request'] = self.request
        ctx['response'] = self.response
        ctx['params'] = self.request.params
        ctx['errors'] = self.errors
        urls = ctx.get("urls")
        if urls is None:
            logger.debug("_get_context: urls is None. Building new collection")
            urls = gripe.url.UrlCollection("root")
        else:
            logger.debug("_get_context: urls already present in context")
        assert urls is not None, "Hrm. urls is still None"
        urls.uri_factory(self)
        if self.user is not None and hasattr(self.user, "urls"):
            u = self.user.urls()
            logger.debug("user urls: %s", u)
            urls.copy(u)
        elif self.user is not None:
            logger.debug("User %s (of type %s) has no urls() method", self.user, self.user.__class__.__name__)
        else:
            logger.debug("self.user is None.")
        if hasattr(self, "urls") and callable(self.urls):
            urls.copy(self.urls())
        logger.debug("urls: %s", urls)
        ctx["urls"] = urls
        if hasattr(self, "get_context") and callable(self.get_context):
            ctx = self.get_context(ctx)
        return ctx

    def _get_template(self):
        ret = self.template \
            if hasattr(self, "template") \
            else None
        if not ret:
            if hasattr(self, "get_template") and callable(self.get_template):
                ret = self.get_template()
            else:
                ret = None
        cname = self.__class__.__name__.lower()
        if not ret:
            module = self.__class__.__module__.lower()
            ret = module + "." + cname if module != '__main__' else cname
        ret = ret.replace(".", "/")
        ret = gripe.Config.app.get(cname, ret)
        logger.info("ReqHandler: using template %s", ret)
        return ret

    def _get_content_type(self):
        if hasattr(self, "get_content_type") and callable(self.get_content_type):
            return self.get_content_type()
        elif hasattr(self, "content_type"):
            return self.content_type
        else:
            content_type = gripe.ContentType.for_path(self.request.path)
            return content_type.content_type if content_type else "text/plain"

    def json_dump(self, obj):
        if obj:
            # logger.info("retstr=%s", json.dumps(obj))
            self.response.content_type = "text/json"
            self.response.json = obj
        else:
            self.status = "204 No Content"

    def render(self):
        ctx = self._get_context()
        self.response.content_type = self._get_content_type()
        if hasattr(self, "get_headers") and callable(self.get_headers):
            headers = self.get_headers(ctx)
            if headers:
                for header in headers:
                    self.response.headers[header] = headers[header]
        self.response.out.write(self._get_env().get_template(self._get_template() + "." + self.file_suffix).render(ctx))


### FIXME
class ErrorPage(ReqHandler):
    content_type = "text/html"

    def __init__(self, status, request, response, exception):
        super(ErrorPage, self).__init__()
        self.status = status
        self.exception = exception
        super(ErrorPage, self).initialize(request, response)

    def get_template(self):
        return "error_%s" % self.response.status_int

    def get(self):
        logger.info("main::ErrorPage_%s.get", self.status)
        self.render({"request": self.request, "response": self.response})


def handle_404(request, response, exception):
    # logger.exception(exception)
    logger.info("404 for %s", request.path_qs)
    # handler = ErrorPage(404, request, response, exception)
    # handler.get()
    response.set_status(404)
