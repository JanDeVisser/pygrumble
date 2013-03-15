__author__="jan"
__date__ ="$18-Feb-2013 11:06:29 AM$"

import importlib
import json
import logging
import os
import os.path
import sys

import gripe.json_util

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

def write_file(fname, data, mode):
    filename = os.path.join(root_dir(), fname)
    with open(filename, mode) as fp:
        return fp.write(data)

def resolve(funcname, default = None):
    if funcname:
        (module, dot, fnc) = funcname.rpartition(".")
        logger.debug("resolve(%s): Importing module %s and getting function %s", funcname, module, fnc)
        mod = importlib.import_module(module)
        return getattr(mod, fnc) if (hasattr(mod, fnc) and callable(getattr(mod, fnc))) else default
    else:
        return resolve(default, None) if isinstance(default, basestring) else default

class ContentType(object):
    Binary, Text = range(2)
    _by_ext = {}
    _by_content_type = {}
    
    def __init__(self, ext, ct, type):
        self.content_type = ct
        self.extension = ext
        self.type = type
        ContentType._by_ext[ext] = self
        ContentType._by_content_type[ct] = self

    def is_text(self):
        return self.type == ContentType.Text

    def is_binary(self):
        return self.type == ContentType.Binary

    @classmethod
    def for_extension(cls, ext, default = None):
        return ContentType._by_ext.get(ext, default)

    @classmethod
    def for_path(cls, path, default = None):
        (fname, ext) = os.path.splitext(path)
        return cls.for_extension(ext, default)

    @classmethod
    def for_content_type(cls, ct, default = None):
        return cls._by_content_type.get(ct, default)

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
    def get_key(cls, key):
        keypath = key.split(".")
        obj = cls
        for p in keypath:
            if hasattr(obj, p):
                obj = getattr(obj, p)
            else:
                return None
        return obj

    @classmethod
    def resolve(cls, path, default = None):
        value = cls.get_key(path)
        logger.debug("Config.resolve(get_key(%s) --> %s)", path, value)
        return resolve(value, default)

    @classmethod
    def _load(cls):
        for f in os.listdir("%s/conf" % root_dir()):
            (section, ext) = os.path.splitext(f)
            if ext == ".json":
                print >> sys.stderr, "Reading conf file %s.json" % section
                config = gripe.json_util.JSON.file_read("conf/%s.json" % section)
                if config and ("components" in config) and isinstance(config.components, list):
                    for component in config.components:
                        comp = gripe.json_util.JSON.file_read("conf/%s.comp" % component)
                        if comp:
                            config.merge(comp)
                    del config["components"]
                setattr(cls, section, config)
        cls._loaded = True

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

# Configure logging

_log_level = None
_log_date_fmt = '%Y-%m-%d %H:%M:%S'
_log_root_fmt = '%(name)-12s:%(asctime)s:%(levelname)-7s:%(message)s'
_log_sub_fmt = '%(asctime)s:%(levelname)-7s:%(message)s'

def get_logger(name):
    global _log_level
    if _log_level is None:
        _log_level = logging.INFO
        if hasattr(Config, "logging") and hasattr(Config.logging, "level"):
            _log_level = getattr(logging, Config.logging.level.upper())
        logging.basicConfig(stream = sys.stderr, level = _log_level, datefmt = _log_date_fmt, format = _log_root_fmt)

    logger = logging.getLogger(name)
    assert logger, "logging.getLogger(%s) returned None" % name
    logger.propagate = False
    formatter = logging.Formatter(_log_sub_fmt, _log_date_fmt)
    destination = "stderr"
    level = _log_level
    if hasattr(Config, "logging") and name in Config.logging:
        level = Config.logging[name].level
        level = getattr(logging, level.upper()) if level else _log_level
        if "destination" in Config.logging[name]:
            destination = Config.logging[name].destination
        assert destination in ("stderr", "file"), "Invalid logging destination %s" % destination
    logger.setLevel(level)
    if "file" in destination:
        try:
            os.mkdir("%s/logs" % root_dir())
        except:
            # Ignored. Probably already exists
            pass
        append = Config.logging[name].append if Config.logging[name].append is not None else False
        mode = "a" if append else "w"
        fh = logging.FileHandler("%s/logs/%s.log" % (root_dir(), name), mode)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    else:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger
    
logger = get_logger(__name__)