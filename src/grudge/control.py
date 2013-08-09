# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$7-Aug-2013 2:21:58 PM$"

import gripe
import grit
import grumble

logger = gripe.get_logger(__name__)

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
            self._template = kwargs.get("fail_template")
        else:
            self._kind = kwargs.get("kind", "grudge.process")
            self._template = kwargs.get("fail_template")
            logger.debug("No process")
        self.render()

    def post(self, key = None):
        return self.get(key)


