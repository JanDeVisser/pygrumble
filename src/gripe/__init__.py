__author__="jan"
__date__ ="$18-Feb-2013 11:06:29 AM$"

import json
import logging
import os
import os.path
import sys

import gripe.json_utils

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


class ContentType(object):
    Binary, Text = range(2)

    def __init__(self, ext, ct, type):
        self.content_type = ct
        self.extension = ext
        self.type = type
        _by_ext[ext] = self
        _by_content_type[ct] = self

    def is_text(self):
        return self.type == Text

    def is_binary(self):
        return self.type == Binary

    @classmethod
    def for_extension(cls, ext, default = None):
        return _by_ext.get(ext, default)

    @classmethod
    def for_path(cls, path, default = None):
        (fname, ext) = os.path.splitext(path)
        return cls.for_extension(ext, default)

    @classmethod
    def for_content_type(cls, ct, default = None):
        return _by_content_type.get(ct, default)

JSON = ContentType(".json", "application/json", ContentType.Text)
JPG = ContentType(".jpg", "image/jpeg", ContentType.Binary)
GIF = ContentType(".gif", "image/gif", ContentType.Binary)
PNG = ContentType(".png", "image/png", ContentType.Binary)
JS = ContentType(".js", "text/javascript", ContentType.Text)
CSS = ContentType(".css", "text/css", ContentType.Text)
XML = ContentType(".xml", "text/xml", ContentType.Text)
TXT = ContentType(".txt", "text/plain", ContentType.Text)
HTML = ContentType(".html", "text/html", ContentType.Text)

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
            (section, ext) = os.path.splitext(f)
            if ext == ".json":
                datastr = read_file("conf/%s.json" % section)
                if datastr:
                    config = gripe.json_utils.JSON.load(datastr if datastr else {})
                    setattr(cls, section, config)


class Enum(tuple):
    """
    Enum class, from here: http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python

    >>> State = Enum(['Unclaimed', 'Claimed'])
    >>> State.Claimed
    1
    >>> State[1]
    'Claimed'
    >>> State
    ('Unclaimed', 'Claimed')
    >>> range(len(State))
    [0, 1]
    >>> [(k, State[k]) for k in range(len(State))]
    [(0, 'Unclaimed'), (1, 'Claimed')]
    >>> [(k, getattr(State, k)) for k in State]
    [('Unclaimed', 0), ('Claimed', 1)]
    """
    __getattr__ = tuple.index
