# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$7-Aug-2013 2:21:58 PM$"

import json

import gripe
import grit
import grumble

logger = gripe.get_logger(__name__)

class Startup(grit.ReqHandler):
    def get_template(self):
        if hasattr(self, "_wf"):
            return self._template or self._wf.kind().replace('.', '/') + "/startup"
        else:
            return self._template or "/grudge/startup_failed"

    def get_context(self, ctx):
        ctx["wf"] = self._wf if hasattr(self, "_wf") else None
        ctx["process"] = self._process if hasattr(self, "_process") else None
        return ctx

    def get(self, process = None, **kwargs):
        self._wf = gripe.resolve(process)
        logger.debug("%s --> grudge.control.Startup::get", self.request.path)
        self._template = kwargs.get("template")
        self.render()

    def post(self, **kwargs):
        logger.debug("%s --> grudge.control.Startup::post", self.request.path)
        if not self.request.headers.get("ST-JSON-Request"):
            logger.debug("Non-JSON post to %s", self.request.path)
            params = self.request.params
            do_json = False
        else:
            logger.debug("%s: JSON body %s", self.request.path, self.request.body)
            params = json.loads(self.request.body)
            do_json = True
        logger.debug("%s: params %s", self.request.path, params)

        self._wf = gripe.resolve(kwargs.get("process"))
        if self._wf:
            self._process = self._wf.instantiate()
            mapping = kwargs.get("mapping", [])
            for param in mapping:
                val = params.get(param)
                try:
                    mapped = mapping[param] or param
                except:
                    mapped = param
                setattr(self._process, mapped, val)
            self._process.put()
            self._process.start()
            if do_json:
                self.json_dump({ "status": "OK" })
            else:
                self._template = kwargs.get("started_template", kwargs.get("template"))
                self.render()
        else:
            logger.error("No process defined")
            self.response_status_int = 500

class AddStatus(grit.ReqHandler):
    def get_template(self):
        if self._process is not None and self._process.exists() and self._process.has_status(self._status):
            return self._template or self._kind.replace('.', '/') + '/' + self._status
        else:
            if self._process is None:
                logger.debug("get_template: _process is None")
            elif not self._process.exists():
                logger.debug("get_template: _process does not exist")
            elif not self._process.has_status(self._status):
                logger.debug("get_template: _process does not have status")
            return self._template or "/grudge/add_status_failed"

    def get_context(self, ctx):
        ctx["process"] = self._process
        ctx["status"] = self._status
        return ctx

    def get(self, code = None, **kwargs):
        assert "status" in kwargs, "No status defined for AddStatus request %s" % self.request
        self._status = kwargs.get("status")
        logger.debug("AddStatus.get(%s) => %s", code, self._status)
        self._process = grumble.Model.get(code) if code else None
        if self._process and self._process.exists():
            logger.debug("Process exists. Setting status %s", self._status)
            self._kind = self._process.kind()
            self._process.add_status(self._status)
            self._template = kwargs.get("success_template")
        else:
            self._kind = kwargs.get("kind", "grudge.process")
            self._template = kwargs.get("fail_template")
            logger.debug("No process")
        self.render()

    def post(self, key = None):
        return self.get(key)


