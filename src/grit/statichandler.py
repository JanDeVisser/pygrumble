# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.


import hashlib
import os.path

import gripe
import grit.requesthandler

__author__="jan"
__date__ ="$19-Sep-2013 4:47:28 PM$"

logger = gripe.get_logger(__name__)


class StaticHandler(grit.requesthandler.ReqHandler):
    etags = {}

    def get(self, *args, **kwargs):
        logger.info("StaticHandler.get(%s)", self.request.path)
        path = ''
        if "abspath" in kwargs:
            path = kwargs["abspath"]
        else:
            path = gripe.root_dir()
            if "relpath" in kwargs:
                path = os.path.join(path, kwargs["relpath"])
        path += self.request.path if not kwargs.get('alias') else kwargs.get("alias")
        if not os.path.exists(path):
            logger.info("Static file %s does not exist", path)
            self.request.response.status = "404 Not Found"
        else:
            if_none_match = self.request.if_none_match
            hashvalue = self.etags.get(path)
            if if_none_match and hashvalue and hashvalue in if_none_match:
                logger.debug("Client has up-to-date resource %s: %s %s", path, if_none_match, hashvalue)
                self.response.status = "304 Not Modified"
            else:
                self.response.content_length = str(os.path.getsize(path))
                content_type = gripe.ContentType.for_path(path)
                self.response.content_type = content_type.content_type
                if content_type.is_text():
                    self.response.charset = "utf-8"
                    mode = "r"
                else:
                    mode = "rb"
                with open(path, mode) as fh:
                    buf = fh.read()
                if path not in self.etags:
                    hashvalue = hashlib.md5(buf).hexdigest()
                    self.etags[path] = hashvalue
                    if if_none_match and hashvalue in if_none_match:
                        logger.debug("Client has up-to-date resource %s. I had to hash it though. %s %s", path, if_none_match, hashvalue)
                        self.response.status = "304 Not Modified"
                        return
                self.response.etag = hashvalue
                self.response.body = str(buf)

