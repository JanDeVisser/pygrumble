#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import sys
import os.path
# if os.path.dirname(__file__) not in sys.path:
#    sys.path.insert(0, os.path.dirname(__file__))
# print sys.path

import os
import re
import gripe
import grit
import grumble

from grumble import image

if __name__ != '__main__':
    import autoreload
    autoreload.start(interval = 1.0)
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/app.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/database.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/logging.json'))
    autoreload.track(os.path.join(os.path.dirname(__file__), 'conf/model.json'))

app = grit.app

if __name__ == '__main__':
    import webapp2

    request = webapp2.Request.blank('/')
    response = request.get_response(app)
    # print response
    assert response.status_int == 302, "Expected 302 Moved Temporarily, got %s" % response.status

    cookie = response.headers["Set-Cookie"]
    parts = cookie.split(";")
    cookie = parts[0]
    location = response.headers["Location"]
    assert location == "http://localhost/login", "Expected to be redirected to /login, but got redirected to %s instead" % location
    print "Requested / and got redirected to /login"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = cookie
    print request.cookies['grit']
    response = request.get_response(app)
    # print response
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print "Requested /login and got OK"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = cookie
    request.method = "POST"
    request.POST["userid"] = "jan@de-visser.net"
    request.POST["password"] = "wbw417"
    request.POST["remember"] = "X"
    response = request.get_response(app)
    # print response
    assert response.status_int == 302, "Expected 302 Moved Temporarily, got %s" % response.status
    location = response.headers["Location"]
    assert location == "http://localhost/"
    print "POSTed login data and got redirected to /"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print response.body
    # assert re.match(u"Really", response.body)
    print "Requested / and got OK"

    request = webapp2.Request.blank("/image/throbber.gif")
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "/image/throbber.gif: Expected 200 OK, got %s" % response.status
    print "Requested /image/throbber.gif and got OK"

    request = webapp2.Request.blank("/css/gristle.css")
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "/css/gristle.css: Expected 200 OK, got %s" % response.status
    print "Requested /css/gristle.css and got OK"

    class Test(grumble.Model):
        quux = grumble.StringProperty()
        froz = grumble.IntegerProperty()
        icon = image.ImageProperty()

    request = webapp2.Request.blank("/json/test", POST = '{ "quux": "Jan de Visser", "froz": 42 }')
    request.headers['Cookie'] = cookie
    request.method = "POST"
    request.content_type = "application/x-www-form-urlencoded"
    request.charset = "utf8"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    d = response.json
    print "Created Test and got OK"

    request = webapp2.Request.blank("/json/test/%s" % d["key"])
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    d = response.json
    print "Requested Test and got OK"

    d["froz"] = 43
    request = webapp2.Request.blank("/json/test")
    request.headers['Cookie'] = cookie
    request.method = "POST"
    request.content_type = "application/x-www-form-urlencoded"
    request.charset = "utf8"
    request.json = d
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    d = response.json
    k = d["key"]
    print "Updated Test and got OK"

    with open("%s/image/Desert.jpg" % gripe.root_dir(), "rb") as fh:
        img = fh.read()
    request = webapp2.Request.blank("/img/test/icon/%s" % k, POST = { "contentType": "image/jpeg", "image": ("Desert.jpg", img) })
    request.headers['Cookie'] = cookie
    request.method = "POST"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print "Updated Test with image and got OK"

    try:
        os.remove("image/Desert_1.jpg")
    except:
        pass

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    etag = response.etag
    with open("%s/image/Desert_1.jpg" % gripe.root_dir(), "wb") as fh:
        fh.write(response.body)
    print "Downloaded Test image and got OK"

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = cookie
    request.if_none_match = etag
    response = request.get_response(app)
    assert response.status_int == 304, "Expected 304 Not Modified, got %s" % response.status
    print "Downloaded Test image again and got Not Modified"

    with open("%s/image/Koala.jpg" % gripe.root_dir(), "rb") as fh:
        img = fh.read()
    request = webapp2.Request.blank("/img/test/icon/%s" % k, POST = { "contentType": "image/jpeg", "image": ("Koala.jpg", img) })
    request.headers['Cookie'] = cookie
    request.method = "POST"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print "Updated Test with new image and got OK"

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = cookie
    request.if_none_match = etag
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK, got %s" % response.status
    print "Downloaded new Test image and got OK"

#    request = webapp2.Request.blank("/json/test/%s" % k)
#    request.headers['Cookie'] = "grit=%s" % cookie
#    request.method = "DELETE"
#    response = request.get_response(app)
#    assert response.status_int == 200, "Expected OK"

    print "all done"
