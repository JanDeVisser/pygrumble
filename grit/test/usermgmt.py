__author__="jan"
__date__ ="$25-Jul-2013 1:06:37 PM$"

import sys

if __name__ != '__main__':
    print "Get off my lawn, punk!"
    sys.exit(0)

import webapp2
import time
import re
import grit

import poplib
import email.parser


def get_messages():
    pop_conn = poplib.POP3_SSL('pop.gmail.com')
    pop_conn.user('runnr@de-visser.net')
    pop_conn.pass_('runnr123')
    #Get messages from server:
    messages = [pop_conn.retr(i) for i in range(1, len(pop_conn.list()[1]) + 1)]
    # Concat message pieces:
    messages = ["\n".join(mssg[1]) for mssg in messages]
    #Parse message intom an email object:
    messages = [email.parser.Parser().parsestr(mssg) for mssg in messages]
    pop_conn.quit()
    return messages

def get_confirmation_url():
    get_messages()

# Clean inbox:
messages = get_messages()
for message in messages:
    print message['subject']

app = grit.app

print "Get landing page"
request = webapp2.Request.blank('/')
response = request.get_response(app)
# print response
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
cookie = response.headers["Set-Cookie"]
parts = cookie.split(";")
cookie = parts[0]

print "Doing signup request"
request = webapp2.Request.blank("/um/signup", POST = """
    {
        "userid": "runnr@de-visser.net",
        "display_name": "Signup Test User",
        "password": "x"
    }
""")
request.headers['ST-JSON-Request'] = "True"
request.method = "POST"
request.content_type = "application/x-www-form-urlencoded"
request.charset = "utf8"
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Submitted signup request"

url = None
while not url:
    time.sleep(10)
    print "Checking mail"
    messages = get_messages()
    for message in messages:
        print "Message:", message["subject"]
        subj = message["subject"]
        if subj == "Confirm your registration with Grumble test app":
            url = message["X-ST-URL"]
            print "url:", url
        else:
            print "Spam"

print "Confirming signup request"
request = webapp2.Request.blank(url)
request.method = "GET"
request.charset = "utf8"
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Confirmed signup request"

time.sleep(10)

print "Logging into application"
request = webapp2.Request.blank("/login")
#request.headers['Cookie'] = cookie
response = request.get_response(app)
# print response
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Requested /login and got OK"

location = "/"
request = webapp2.Request.blank("/login")
#request.headers['Cookie'] = cookie
request.method = "POST"
request.POST["userid"] = "runnr@de-visser.net"
request.POST["password"] = "x"
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

location = "**"
print "Logging out"
request = webapp2.Request.blank("/logout")
request.headers['Cookie'] = cookie
response = request.get_response(app)
assert response.status_int in [200, 302], "Expected 200 OK or 302 Redirected, got %s" % response.status
location = response.headers["Location"] if response.status_int == 302 else location
print "Logged out, redirecting to ", location



print "Password Reset"
request = webapp2.Request.blank("/um/reset", POST = '{ "userid": "runnr@de-visser.net" }')
request.headers['ST-JSON-Request'] = "True"
request.method = "POST"
request.content_type = "application/x-www-form-urlencoded"
request.charset = "utf8"
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
print "Submitted reset request"

url = None
while not url:
    time.sleep(10)
    print "Checking mail"
    messages = get_messages()
    for message in messages:
        print "Message:", message["subject"]
        subj = message["subject"]
        if subj == "New password request for Grumble test app":
            url = message["X-ST-URL"]
            print "url:", url
        else:
            print "Spam"

print "Confirming reset request"
request = webapp2.Request.blank(url)
request.method = "GET"
request.charset = "utf8"
response = request.get_response(app)
assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
password = response.headers["X-ST-Password"]
print "Confirmed reset request. New password is ", password

print "Logging in with generated password"
location = "/"
request = webapp2.Request.blank("/login")
request.method = "POST"
request.POST["userid"] = "runnr@de-visser.net"
request.POST["password"] = password
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

print "Changing password"
request = webapp2.Request.blank("/um/changepwd")
request.headers['Cookie'] = cookie
request.method = "POST"
request.POST["oldpassword"] = password
request.POST["newpassword"] = "xx"
response = request.get_response(app)
assert response.status_int in [200, 302], "Expected 200 OK or 302 Redirected, got %s" % response.status
location = response.headers["Location"] if response.status_int == 302 else location
print "Logged out, redirecting to ", location

location = "**"
print "Logging out"
request = webapp2.Request.blank("/logout")
request.headers['Cookie'] = cookie
response = request.get_response(app)
assert response.status_int in [200, 302], "Expected 200 OK or 302 Redirected, got %s" % response.status
location = response.headers["Location"] if response.status_int == 302 else location
print "Logged out, redirecting to ", location

print "Logging in with new password"
location = "/"
request = webapp2.Request.blank("/login")
request.method = "POST"
request.POST["userid"] = "runnr@de-visser.net"
request.POST["password"] = "xx"
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

location = "**"
print "Logging out"
request = webapp2.Request.blank("/logout")
request.headers['Cookie'] = cookie
response = request.get_response(app)
assert response.status_int in [200, 302], "Expected 200 OK or 302 Redirected, got %s" % response.status
location = response.headers["Location"] if response.status_int == 302 else location
print "Logged out, redirecting to ", location

