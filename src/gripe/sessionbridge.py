# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$16-Feb-2013 10:00:26 PM$"

class SessionBridge(object):
    def __init__(self, userid, roles):
        self._userid = userid
        self._roles = roles

    def userid(self):
        return self._userid

    def roles(self):
        return self._roles

def login(userid, roles):
    global sessionbridge
    sessionbridge = SessionBridge(userid, roles)

login("test@grumble.net", ["admin", "user"])
