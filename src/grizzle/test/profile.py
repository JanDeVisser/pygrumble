__author__="jan"
__date__ ="$25-Jul-2013 1:06:37 PM$"

import sys

import json
import webapp2
import time
import grit
import grizzle

app = grit.app

def request_json_data(location, cookie, query):
    print "Getting JSON data from ", location
    print "JSON query", query
    request = webapp2.Request.blank(location)
    request.headers['ST-JSON-Request'] = json.dumps(query)
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print "Requested JSON data from", location, " and got OK"
    ret = json.loads(response.body)
    print "Returned JSON data", ret
    return ret



print "Get landing page"
request = webapp2.Request.blank('/')
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status


print "Logging into application"
request = webapp2.Request.blank("/login")
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Requested /login and got OK"

location = "/"
request = webapp2.Request.blank("/login")
request.method = "POST"
request.POST["userid"] = "jan@de-visser.net"
request.POST["password"] = "wbw417"
request.POST["remember"] = "x"
response = request.get_response(app)
print response.status_int
location = response.headers["Location"] if response.status_int == 302 else location
cookie = response.headers["Set-Cookie"]
parts = cookie.split(";")
cookie = parts[0]
print "POSTed login data"

print "Getting", location
request = webapp2.Request.blank(location)
request.headers['Cookie'] = cookie
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Requested / and got OK"

users = request_json_data("/json/user", cookie, {})
assert users, "Expected at least one user"
user = users[0]
user_data = request_json_data("/json/user/%s" % user["key"], cookie, 
    {"_flags": {"include_parts": True }})