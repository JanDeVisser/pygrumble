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

import os.path
import webapp2

import gripe
import gripe.role
import grit.handlers
import grudge
import grumble
import grumble.image

logger = gripe.get_logger(__name__)


class UploadedFile(grumble.Model):
    timestamp = grumble.DateTimeProperty(auto_now=True)
    user = grumble.StringProperty()
    process = grumble.StringProperty()
    filename = grumble.StringProperty()
    content_type = grumble.StringProperty()
    content = grumble.image.BinaryProperty()

    def get_user(self):
        return grit.role.Guard.get_usermanager().get(self.user)


class Uploader(grit.handlers.BridgedHandler):
    def post(self, process=None):
        logger.info("Uploader.post(%s:%s)", process)
        if not self.user:
            self.error(401)
        elif not process:
            logger.error("No process specified for upload")
            self.error(500)
        else:
            process_class = gripe.resolve(process)
            if not process_class:
                logger.error("Process class '%s' specified in upload not found", process)
                self.error(500)
            elif not grudge.is_process(process_class):
                logger.error("Class '%s' specified as process class in upload is not a grudge process class", process)
                self.error(500)
            else:
                for upload in self.request.POST.getall("file"):
                    uploaded_file = UploadedFile()
                    uploaded_file.user = self.user.uid()
                    uploaded_file.process = process
                    uploaded_file.content = upload.file.read()
                    uploaded_file.filename = os.path.basename(upload.filename)
                    uploaded_file.content_type = upload.type
                    uploaded_file.put()
                    p = process_class.instantiate(uploadedFile=uploaded_file)
                    p.start()

app = webapp2.WSGIApplication([
        webapp2.Route(r'/upload/<process>', handler=Uploader, name='uploader'),
    ], debug=True)
