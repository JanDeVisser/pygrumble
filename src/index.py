#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$26-Jan-2013 9:47:24 PM$"

import webapp2

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write("""
        <html>
            <h1> I T  W O R K S !</h1>
            Really !!!!
        </html>
        """)

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(app, host='127.0.0.1', port='8080')
