import grumble

class HttpAccess(grumble.Model):
    _flat = True
    _audit = False
    timestamp = grumble.DateTimeProperty(auto_now_add = True)
    remote_addr = grumble.TextProperty()
    user = grumble.TextProperty()
    path = grumble.TextProperty()
    method = grumble.TextProperty()
    status = grumble.TextProperty()

class HttpAccessLogger(object):
    def log(self, reqctx):
        request = reqctx.request
        response = reqctx.response
        with grumble.Tx.begin():
            access = HttpAccess()
            access.remote_addr = request.remote_addr
            access.user = reqctx.user.uid() if (hasattr(reqctx, "user") and reqctx.user) else None
            access.path = request.path_qs
            access.method = request.method
            access.status = response.status
            access.put()

