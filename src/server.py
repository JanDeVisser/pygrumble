#! /usr/bin/python

# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$22-Feb-2013 8:59:24 AM$"

from paste import httpserver
import grit

if __name__ == "__main__":
    app = grit.WSGIApplication(debug=True)
    httpserver.serve(app, host='127.0.0.1', port='8080')
