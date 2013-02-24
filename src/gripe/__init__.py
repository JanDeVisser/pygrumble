__author__="jan"
__date__ ="$18-Feb-2013 11:06:29 AM$"

import json
import logging
import os
import os.path
import sys


logging.basicConfig(level = logging.DEBUG, datefmt = '%Y-%m-%d %H:%M:%S', \
    format = '%(asctime)s %(levelname)-8s %(message)s')

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class NotSerializableError(Error):
    """Marker exception raised when when a non-JSON serializable property is
    serialized"""
    def __init__(self, propname):
        self.propname = propname

    def __str__(self):
        return "Property %s is not serializable" % (self.propname, )

_root_dir = None
def root_dir():
    global _root_dir
    if not _root_dir:
        modfile = sys.modules["gripe"].__file__
        _root_dir = os.path.dirname(modfile)
        _root_dir = os.path.dirname(_root_dir) if _root_dir != modfile else '..'
        logging.info("root dir: %s", _root_dir)
    return _root_dir
#       logging.info("os.getcwd(): %s", os.getcwd())
#   return os.getcwd()

def read_file(fname):
    try:
        filename = os.path.join(root_dir(), fname)
        fp = open(filename, "rb")
    except IOError as e:
        #print "IOError reading config file %s: %s" % (filename, e.strerror)
        return None
    else:
        with fp:
            return fp.read()


_content_types = {
    "json": "application/json",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "png": "image/png",
    "js": "text/javascript",
    "css": "text/css",
    "xml": "text/xml",
    "txt": "text/plain",
    "html": "text/html"
}
def get_content_type(disposition):
    (fname, dot, ext) = disposition.rpartition(".")
    return _content_types.get(ext, "text/plain")

class ConfigMeta(type):
    def __getattribute__(cls, name):
        if not super(ConfigMeta, cls).__getattribute__("_loaded"):
            super(ConfigMeta, cls).__getattribute__("_load")()
        return super(ConfigMeta, cls).__getattribute__(name)

class Config(object):
    __metaclass__ = ConfigMeta
    _loaded = False

    @classmethod
    def _load(cls):
        for f in os.listdir("%s/conf" % root_dir()):
            if f.endswith(".json"):
                (section, dot, ext) = f.partition(".")
                datastr = read_file("conf/" + section + ".json")
                if datastr:
                    config = json.loads(datastr) if datastr else {}
                    setattr(cls, section, config)
