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

import gripe
import grumble
import grudge

logger = gripe.get_logger(__name__)

if __name__ == "__main__":

    @grudge.Process(entrypoint="Step1")
    class WF(grumble.Model):
        pass

    @grudge.OnStarted(grudge.Transition("../Step2"))
    @grudge.Process(parent="WF")
    class Step1(grumble.Model):
        pass

    @grudge.OnStarted(grudge.Invoke(".:set_recipients"))
    @grudge.OnAdd("sendmail", grudge.SendMail(recipients="@recipients",
                  subject="Grudge Test", text="This is a test", status="stopme"))
    @grudge.OnAdd("stopme", grudge.Stop())
    @grudge.OnStopped(grudge.Transition("../Step3"))
    @grudge.Process(parent="WF")
    class Step2(grumble.Model):
        sendmail = grudge.Status()
        stopme = grudge.Status()
        recipients = grumble.TextProperty()

        def set_recipients(self):
            self.recipients = "sweattrails@de-visser.net"
            self.put()
            return self.sendmail

    @grudge.OnStarted(grudge.Add("startme"))
    @grudge.OnAdd("startme", grudge.Remove("startme"))
    @grudge.OnRemove("startme", grudge.Stop())
    @grudge.Process(parent="WF", exitpoint=True)
    class Step3(grumble.Model):
        startme = grudge.Status()

    wf = WF.instantiate()
    wf.start()

    grudge.wait()
