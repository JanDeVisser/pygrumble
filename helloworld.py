import webapp2

def application(environ, start_response):
    status = '200 OK'
    output = b'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


class HelloWorld(webapp2.RequestHandler):
    def get(self):
        self.response.content_type = "text/plain"
        self.response.text = u"Hallo Wereld"

app = webapp2.WSGIApplication([('/', HelloWorld), ('/foo', HelloWorld)],
                              debug = True)
