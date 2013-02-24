#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

import grit
import grumble
import re

from grumble import image

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
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    #print response
    assert response.status_int == 200, "Expected OK"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "POST"
    request.POST["userid"] = "jan@de-visser.net"
    request.POST["password"] = "wbw417"
    response = request.get_response(app)
    #print response
    assert response.status_int == 302, "Expected to be redirected"
    location  = response.headers["Location"]
    assert location == "http://localhost/"

    request = webapp2.Request.blank(location)
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    print response.body
    #assert re.match(u"Really", response.body)

    request = webapp2.Request.blank("/conf/app.json")
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "/conf/app.json: Expected 200 OK, got %s" % response.status

    request = webapp2.Request.blank("/grit/template/login.html")
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "/grit/template/login.html Expected 200 OK, got %s" % response.status
    print response.body

    class Test(grumble.Model):
        quux = grumble.StringProperty()
        froz = grumble.IntegerProperty()
        icon = image.ImageProperty()

    request = webapp2.Request.blank("/json/test", POST = '{ "quux": "Jan de Visser", "froz": 42 }')
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "POST"
    request.content_type = "application/x-www-form-urlencoded"
    request.charset = "utf8"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    d = response.json

    request = webapp2.Request.blank("/json/test/%s" % d["key"])
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    d = response.json

    d["froz"] = 43
    request = webapp2.Request.blank("/json/test")
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "POST"
    request.content_type = "application/x-www-form-urlencoded"
    request.charset = "utf8"
    request.json = d
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    d = response.json
    print d
    k = d["key"]

    with open("C:/Users/Public/Pictures/Sample Pictures/Desert.jpg", "rb") as fh:
        img = fh.read()
    request = webapp2.Request.blank("/img/test/icon/%s" % k, POST = { "contentType": "image/jpeg", "image": ("Desert.jpg", img) })
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "POST"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"

    try:
        os.remove("C:/Users/Public/Pictures/Sample Pictures/Desert_1.jpg")
    except:
        pass

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = "grit=%s" % cookie
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"
    etag = response.etag
    with open("C:/Users/Public/Pictures/Sample Pictures/Desert_1.jpg", "wb") as fh:
        fh.write(response.body)

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = "grit=%s" % cookie
    request.if_none_match = etag
    response = request.get_response(app)
    print response.status
    assert response.status_int == 304, "Expected 304 Not Modified"

    with open("C:/Users/Public/Pictures/Sample Pictures/Koala.jpg", "rb") as fh:
        img = fh.read()
    request = webapp2.Request.blank("/img/test/icon/%s" % k, POST = { "contentType": "image/jpeg", "image": ("Koala.jpg", img) })
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "POST"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected 200 OK"

    request = webapp2.Request.blank("/img/test/icon/%s" % k)
    request.headers['Cookie'] = "grit=%s" % cookie
    request.if_none_match = etag
    response = request.get_response(app)
    print response.status
    assert response.status_int == 200, "Expected 200 OK"

    request = webapp2.Request.blank("/json/test/%s" % k)
    request.headers['Cookie'] = "grit=%s" % cookie
    request.method = "DELETE"
    response = request.get_response(app)
    assert response.status_int == 200, "Expected OK"

    print "all done"
