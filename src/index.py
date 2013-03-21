#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$26-Jan-2013 9:47:24 PM$"

import webapp2
import grit.handlers

class MainPage(grit.handlers.PageHandler):
    template = "index"

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug = True)

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(app, host = '127.0.0.1', port = '8080')
