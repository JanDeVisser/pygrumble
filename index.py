#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$26-Jan-2013 9:47:24 PM$"

import webapp2
import grit.handlers

class TestPage(grit.handlers.PageHandler):
    template = "test/maps"


class MainPage(grit.handlers.PageHandler):
    template = "index"


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/t/maps.html', TestPage)],
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
