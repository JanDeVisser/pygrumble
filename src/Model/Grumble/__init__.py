__author__="jan"
__date__ ="$30-Jan-2013 12:08:58 PM$"

import logging
import threading

import grumble

class HttpSession(grumble.Model):
    _flat = True
    session_data = grumble.JSONProperty()

class User(grumble.Model):
    _flat = True
    email = grumble.TextProperty(is_key = True)
    password = grumble.PasswordProperty()
    display_name = grumble.TextProperty()
    roles = grumble.ListProperty()
    
    def has_role(self, roles):
        logging.debug("has_role: %s %s %s", set(roles), set(self.roles), set(roles) &  set(self.roles))
        return len(set(roles) & set(self.roles)) > 0

    @classmethod
    def login(cls, email, password):
        hash = grumble.PasswordProperty.hash(password)
        user = User.query("email = ", email, "password = ", hash, ancestor = None)
        if user:
            assert isinstance(user, User), "Huh? More than one user with the same email and password??"
        return user.id() if user else None

class HttpAccess(grumble.Model):
    _flat = True
    _audit = False
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
