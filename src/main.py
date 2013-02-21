#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import grit
import re

app = grit.WSGIApplication(debug=True)

if __name__ == '__main__':
    import webapp2

    request = webapp2.Request.blank('/')
    response = request.get_response(app)
    #print response
    assert response.status_int == 302, "Expected to be redirected"

    cookie = response.headers["Set-Cookie"]
    (junk,sep,cookie) = cookie.partition('"')
    (cookie,sep,junk) = cookie.partition('"')
    cookie = cookie.replace('\\075', '=')
    location  = response.headers["Location"]
    assert location == "http://localhost/login"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    response = request.get_response(app)
    #print response
    assert response.status_int == 200, "Expected OK"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    request.method = "POST"
    request.POST["userid"] = "jan@de-visser.net"
    request.POST["password"] = "wbw417"
    response = request.get_response(app)
    #print response
    assert response.status_int == 302, "Expected to be redirected"
    location  = response.headers["Location"]
    assert location == "http://localhost/"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grumble=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    print response.body
    #assert re.match("Really", response.body)

