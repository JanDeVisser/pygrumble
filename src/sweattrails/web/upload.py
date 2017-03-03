#
# Copyright (c) 2017 Jan de Visser (jan@sweattrails.com)
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

import exceptions

import gripe
import grit.upload
import grizzle
import grumble
import grumble.model
import grudge
import sweattrails.device.exceptions
import sweattrails.device.parser
import sweattrails.session

logger = gripe.get_logger(__name__)


@grudge.Process(entrypoint="Check")
class UploadActivity(grumble.Model):
    uploadedFile = grumble.ReferenceProperty(grit.upload.UploadedFile)
    athlete = grumble.ReferenceProperty(grizzle.User)
    filename = grumble.property.StringProperty()
    converted = grumble.BooleanProperty(default=False)
    error = grumble.TextProperty()


@grudge.OnStarted(grudge.Invoke("./check"))
@grudge.OnAdd("OK", grudge.Transition("../Import"))
@grudge.OnAdd("Error", grudge.Transition("../Finished"))
@grudge.Process(parent="UploadActivity")
class Check(grumble.Model):
    OK = grudge.Status()
    error = grudge.Status()

    def check(self):
        # Initialize parent: filename, athlete
        # Check
        #  - If the user is an athlete
        #  - If the file hasn't been uploaded yet
        return self.OK


@grudge.OnStarted(grudge.Invoke("./import_file"))
@grudge.OnAdd("done", grudge.Transition("../Finished"))
@grudge.Process(parent="UploadActivity")
class Import(grumble.Model):
    done = grudge.Status()

    def import_file(self):
        activity = self.parent()
        uploaded = activity.uploadedFile
        try:
            parser = sweattrails.device.parser.get_parser(uploaded.filename)
            parser.set_athlete(activity.athlete)
            parser.parse()
            activity.converted = True
        except exceptions.Exception as e:
            activity.error = e.message
        activity.put()
        return self.done


@grudge.OnStarted(grudge.Invoke("./cleanup"))
@grudge.OnStarted(grudge.Stop)
@grudge.Process(parent="UploadActivity", exitpoint=True)
class Finished(grumble.Model):
    def cleanup(self):
        grumble.model.delete(self.parent().uploadedFile)
        self.parent().uploadedFile = None
        self.parent().put()
