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

import hashlib
import os.path

import gripe
import grit.requesthandler

logger = gripe.get_logger(__name__)


class StaticHandler(grit.requesthandler.ReqHandler):
    etags = {}

    def get(self, *args, **kwargs):
        request = self.request
        route = request.route
        logger.info("StaticHandler.get(%s)", request.path)
        reqpath = route.grit_params["alias"] if 'alias' in route.grit_params else request.path

        if "abspath" in route.grit_params:
            if reqpath[0] == '/' or reqpath[0] == '\\':
                reqpath = reqpath[1:]
            path = os.path.join(kwargs["abspath"], reqpath)
            logger.debug("Retrieving %s using absolute path %s", path, route.grit_params["abspath"])
        elif "relpath" in route.grit_params:
            prefix = os.path.commonprefix([route.grit_params["path"], reqpath])
            relative = os.path.relpath(reqpath, prefix)
            if relative[0] == '/' or relative[0] == '\\':
                relative = relative[1:]
            relpath = route.grit_params["relpath"]
            if relpath[0] == '/' or relpath[0] == '\\':
                relpath = relpath[1:]
            path = os.path.join(gripe.root_dir(), relpath, relative)
            logger.debug("Mapping '%s' to '%s' using relative path '%s'", reqpath, path, route.grit_params["relpath"])
        else:
            if reqpath[0] == '/' or reqpath[0] == '\\':
                reqpath = reqpath[1:]
            path = os.path.join(gripe.root_dir(), reqpath)
            logger.debug("Joining %s with root_dir %s gives %s", reqpath, gripe.root_dir(), path)

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

