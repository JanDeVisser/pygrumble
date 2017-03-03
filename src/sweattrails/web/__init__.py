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


import webapp2

import grit.handlers
import sweattrails.session


class SessionHandler(grit.handlers.PageHandler):
    def prepare_query(self, q):
        q['"athlete" = '] = str(self.user.key())
        return q


app = webapp2.WSGIApplication([
    webapp2.Route(
        r'/st/activities',
        handler="sweattrails.web.SessionHandler", name='list-activities',
        defaults={
            "kind": sweattrails.session.Session
        }),
    webapp2.Route(
        r'/st/activity/<key>',
        handler="sweattrails.web.SessionHandler", name='manage-activity',
        defaults={
            "kind": sweattrails.session.Session
        }
    )
    ], debug = True)
