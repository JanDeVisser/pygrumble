__author__="jan"
__date__ ="$30-Jan-2013 12:08:58 PM$"

import sha
import threading

import grumble

_tl = threading.local()

class HttpSession(grumble.Model):
    session_data = grumble.JSONProperty()
    created = grumble.DateTimeProperty(auto_now_add = True)
    last_access = grumble.DateTimeProperty(auto_now = True)

class User(grumble.Model):
    email = grumble.TextProperty(Key = True)
    password = grumble.TextProperty()
    display_name = grumble.TextProperty()
    roles = grumble.ListProperty()
    
    def has_role(self, roles):
        return set(roles) &  set(self.roles)

    @classmethod
    def login(cls, email, password):
        user = User.query("email = ", email, "password = ", sha.sha(password).hexdigest(), ancestor = None)
        if user:
            assert isinstance(user, User), "Huh? More than one user with the same email and password??"
            _tl.user = user
        return user.id() if user else None

class HttpAccess(grumble.Model):
    timestamp = grumble.DateTimeProperty(auto_now_add = True)
    remote_addr = grumble.TextProperty()
    user = grumble.TextProperty()
    path = grumble.TextProperty()
    method = grumble.TextProperty()
    status = grumble.TextProperty()

if __name__ == "__main__":
    with grumble.Tx.begin():
        uid = User.login("jan@de-visser.net", "wbw417")
        assert uid, "login returned no User id"
        u = User.get(uid)
        assert u, "uid %s does not map to a User model" % uid
        assert u.email == "jan@de-visser.net", "User has unexpected email address %s" % u.email
        assert u.has_role("admin"), "%s does not have admin role while he should" % u.email
        assert not u.has_role("coach"), "%s does have coach role while he shouldn't" % u.email
        print "All OK"
