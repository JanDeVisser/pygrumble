#
# Copyright (c) 2018 Jan de Visser (jan@sweattrails.com)
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

app = webapp2.WSGIApplication([('/', "grit.handlers.MainPage")],
                              debug = True)

if __name__ == '__main__':
    import os.path

    import paste.httpserver
    import paste.translogger

    import autoreload
    import grit

    autoreload.start(interval=1.0)
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/app.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/database.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/gripe.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/grizzle.inc'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/logging.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/model.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/smtp.json'))

    paste.httpserver.serve(paste.translogger.TransLogger(grit.app),
                           host = '127.0.0.1', port = '8080')
