#
# Copyright (c) 2014 Jan de Visser (jan@sweattrails.com)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#


import errno
import importlib
import json
import logging
import os
import os.path
import sys
import threading
import traceback

import gripe.json_util

#############################################################################
#
#  E X C E P T I O N S
#
#############################################################################

class Error(Exception):
    """
        Base class for exceptions in this module.
    """
    pass

class NotSerializableError(Error):
    """
        Marker exception raised when when a non-JSON serializable property is
        serialized
    """
    def __init__(self, propname):
        self.propname = propname

    def __str__(self):
        return "Property %s is not serializable" % (self.propname,)

class AuthException(gripe.Error):
    pass

#############################################################################
#
##############################################################################


_root_dir = None
def root_dir():
    global _root_dir
    if not _root_dir:
        modfile = sys.modules["gripe"].__file__
        _root_dir = os.path.dirname(modfile)
        _root_dir = os.path.dirname(_root_dir) if _root_dir != modfile else '..'
    return _root_dir

_users_init = set([])
def user_dir(uid):
    if not _users_init:
        mkdir("users")
    userdir = os.path.join("users", uid)
    if uid not in _users_init:
        mkdir(userdir)
        _users_init.add(uid)
    return userdir

def read_file(fname):
    try:
        filename = os.path.join(root_dir(), fname)
        fp = open(filename, "rb")
    except IOError as e:
        # print "IOError reading config file %s: %s" % (filename, e.strerror)
        return None
    else:
        with fp:
            return fp.read()


def write_file(fname, data, mode = "w+"):
    filename = os.path.join(root_dir(), fname)
    with open(filename, mode) as fp:
        return fp.write(data)

def exists(f):
    p = os.path.join(root_dir(), f)
    return os.access(p, os.F_OK)

def unlink(f):
    p = os.path.join(root_dir(), f)
    try:
        if os.access(p, os.F_OK):
            if os.access(p, os.W_OK):
                os.unlink(p)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def rename(oldname, newname):
    o = os.path.join(root_dir(), oldname)
    n = os.path.join(root_dir(), newname)
    try:
        if os.access(o, os.F_OK):
            if os.access(o, os.W_OK):
                if not os.access(n, os.F_OK):
                    os.rename(o, n)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def listdir(dirname):
    return os.listdir(os.path.join(root_dir(), dirname))

def mkdir(dirname):
    try:
        os.mkdir(os.path.join(root_dir(), dirname))
        return True
    except:
        return False


def resolve(funcname, default = None):
    if funcname:
        if callable(funcname):
            return funcname
        (module, dot, fnc) = funcname.rpartition(".")
        mod = importlib.import_module(module)
        return getattr(mod, fnc) if hasattr(mod, fnc) and callable(getattr(mod, fnc)) else default
    else:
        return resolve(default, None) if isinstance(default, basestring) else default


class abstract(object):
    def __init__(self, *args):
        self._methods = args

    def __call__(self, cls):
        for method in self._methods:
            if isinstance(method, tuple):
                m = method[0]
                doc = method[1]
                decorator = getattr(__builtins__, method[2]) if len(method) > 2 else None
            else:
                m = str(method)
                doc = None
                decorator = None
            def wrapper(instance):
                n = instance.__name__ if isinstance(instance, type) else instance.__class__.__name__
                assert 0, "Method %s of class %s is abstract" % (method, n)
            wrapper.__doc__ = doc
            if decorator:
                wrapper = decorator(wrapper)
            setattr(cls, m, wrapper)
        return cls

class LoopDetector(set):
    _tl = threading.local()

    def __init__(self):
        self.count = 0
        self.loop = False
        LoopDetector._tl.detector = self

    def __enter__(self):
        self.count += 1
        return self

    def __exit__(self, *args):
        self.count -= 1
        if not self.count:
            del LoopDetector._tl.detector

    @classmethod
    def begin(cls, obj = None):
        ret = LoopDetector._tl.detector if hasattr(LoopDetector._tl, "detector") else LoopDetector()
        if obj is not None:
            if obj in ret:
                ret.loop = True
            else:
                ret.add(obj)
        return ret

class LoggerSwitcher(object):
    def __init__(self, packages, logger):
        self._backup = {}
        self._packages = packages if isinstance(packages, (list, tuple)) else [packages]
        self._logger = logger

    def __enter__(self):
        for p in self._packages:
            if hasattr(p, "logger"):
                print >> sys.stderr, "Switching logger for package", p.__name__
                self._backup[p] = p.logger
                p.logger = self._logger
        return self

    def __exit__(self, *args):
        for p in self._backup:
            p.logger = self._backup[p]

    @classmethod
    def begin(cls, packages, logger):
        return LoggerSwitcher(packages, logger)

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
        (_, ext) = os.path.splitext(path)
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
        if name in ("backup", "restore", "_sections"):
            return super(ConfigMeta, cls).__getattribute__(name)
        if not super(ConfigMeta, cls).__getattribute__("_loaded"):
            super(ConfigMeta, cls).__getattribute__("_load")()
        return super(ConfigMeta, cls).__getattribute__(name)

    def __setattr__(cls, name, value):
        if not name.startswith("_"):
            cls._sections.add(name)
        return super(ConfigMeta, cls).__setattr__(name, gripe.json_util.JSON.create(value))

    def __delattr__(cls, name):
        cls._sections.remove(name)
        return super(ConfigMeta, cls).__delattr__(name)

    def __len__(cls):
        return len(cls._sections)

    def __getitem__(cls, key):
        return getattr(cls, key)

    def __setitem__(cls, key, value):
        return setattr(cls, key, value)

    def __delitem__(cls, key):
        return delattr(cls, key)

    def __iter__(cls):
        return iter(cls._sections)

    def __contains__(cls, key):
        return key in cls._sections

    def keys(cls):
        return cls._sections

class Config(object):
    __metaclass__ = ConfigMeta
    _loaded = False
    _sections = set([])
    
    # We set a bunch of dummies here to keep IDEs happy:
    logging = {}
    app = {}
    database = {}
    gripe = {}
    grit = {}
    grumble = {}
    model = {}
    qtapp = {}
    smtp = {}
    sweattrails = {}

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
        return resolve(value, default)

    @classmethod
    def as_dict(cls):
        return { section: getattr(cls, section) for section in cls._sections }

    @classmethod
    def as_json(cls):
        return json.dumps(cls.as_dict())

    @classmethod
    def set(cls, section, config):
        config = gripe.json_util.JSONObject(config) \
            if not isinstance(config, gripe.json_util.JSONObject) \
            else config
        if (not exists(os.path.join("conf", "%s.json.backup" % section)) and
                exists(os.path.join("conf", "%s.json" % section))):
            rename(os.path.join("conf", "%s.json" % section),
                   os.path.join("conf", "%s.json.backup" % section))
        config.file_write(os.path.join("conf", "%s.json" % section), 4)
        setattr(cls, section, config)
        return config
    
    @classmethod
    def _load(cls):
        for f in os.listdir(os.path.join(root_dir(), "conf")):
            (section, ext) = os.path.splitext(f)
            if ext == ".json":
                #print >> sys.stderr, "Reading conf file %s.json" % section
                #print "Reading conf file %s.json" % section
                config = gripe.json_util.JSON.file_read(os.path.join("conf", "%s.json" % section))
                if config and ("components" in config) and isinstance(config.components, list):
                    for component in config.components:
                        comp = gripe.json_util.JSON.file_read(os.path.join("conf", "%s.comp" % component))
                        if comp:
                            config.merge(comp)
                    del config["components"]
                # print >> sys.stderr, "Config.%s: %s" % (section, json.dumps(config))
                setattr(cls, section, config)
        # print >> sys.stderr, "Read all conf files"
        cls._loaded = True
        # logging is special. We always want it.
        if not hasattr(cls, "logging"):
            print "Adding dummy logging conf"
            setattr(cls, "logging", gripe.json_util.JSONObject())

    @classmethod
    def backup(cls):
        for s in cls._sections:
            config = getattr(cls, s)
            unlink(os.path.join("conf", "%s.json.backup" % s))
            if config is not None:
                config.file_write(os.path.join("conf", "%s.json.backup" % s), 4)

    @classmethod
    def restore(cls):
        for f in os.listdir(os.path.join(root_dir(), "conf")):
            (section, ext) = os.path.splitext(f)
            if ext == ".json":
                unlink(os.path.join("conf", f))
        for f in os.listdir(os.path.join(root_dir(), "conf")):
            (section, ext) = os.path.splitext(f)
            if ext == ".backup":
                os.rename(os.path.join(root_dir(), "conf", "%s.json.backup" % section),
                          os.path.join(root_dir(), "conf", "%s.json" % section))

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

class LoggerProxy(object):
    def __init__(self, logger):
        self._logger = logger;
        
    def __getattr__(self, name):
        return getattr(self._logger, name)
    
class LogConfig(object):
    _configs = {}
    _defaults = None
    _default_config = {
        "level": logging.INFO, 
        "destination": "stderr",
        "filename": None,
        "append": False,
        "format": "%(name)-15s:%(asctime)s:%(levelname)-7s:%(message)s",
        "dateformat": "%y%m%d %H:%M:%S"
    }
    
    def __init__(self, name = None, config = None):
        if config:
            self._build(name, config)
        else:
            if LogConfig._defaults is None:
                LogConfig._defaults = LogConfig("builtin.defaults", 
                                                LogConfig._default_config)
            self.name = name if name else ""
            self.config = self._get_config()
            self.parent = self._get_parent()
            self._logger = None
            self._handler = None
            
            self.log_level = getattr(logging, self.config["level"].upper()) \
                if "level" in self.config \
                else self.parent.log_level 
                
            self.destination = self.config.get(
                                   "destination", 
                                   self.parent.destination).lower()
            assert self.destination in ("stderr", "file"), \
                    "Invalid logging destination %s" % self.destination
            self.filename = self.config.get("filename")
            self.append = self.config.get("append", self.parent.append)
            self.flat = self.config.get("flat", not bool(self.name))
            self.format = self.config.get("format", self.parent.format)
            self.dateformat = self.config.get("dateformat", self.parent.dateformat)
        
    def _build(self, name, config):
        self.name = name
        self.config = config
        self.parent = None
        self._logger = None
        self._handler = None
        
        self.log_level   = config.get("level")
        self.destination = config.get("destination")
        self.filename    = config.get("filename")
        self.append      = config.get("append")
        self.format      = self.config.get("format")
        self.dateformat  = self.config.get("dateformat")
        self.flat        = True
        
    def _get_config(self):
        ret = Config["logging"].get(self.name) \
            if self.name \
            else Config["logging"].get("__root__")
        return ret or {}
        
    def _get_parent(self):
        if not self.name:
            return LogConfig._defaults
        else:
            (parent, _, _) = self.name.rpartition(".")
            return LogConfig.get(parent)
    
    def _get_filename(self):
        if self.filename or not self.parent:
            return self.filename
        else:
            return self.parent._get_filename()
            
    def get_filename(self):
        ret = self._get_filename()
        if ret is None:
            ret = (self.name if self.name else "__grumble__") + ".log"
        return ret
    
    def _create_file_handler(self):
        mkdir("logs")
        mode = "a" if self.append else "w"
        return logging.FileHandler(os.path.join(root_dir(), "logs", self.get_filename()), mode)
    
    def _create_stderr_handler(self):
        return logging.StreamHandler(sys.stderr)
            
    def _get_handler(self):
        if not self._handler:
            formatter = logging.Formatter(self.format, self.dateformat)
            handler_factory = self._get_handler_factory(self)
            self._handler = handler_factory()
            self._handler.setFormatter(formatter)
        return self._handler
    
    def get_logger(self):
        if not self._logger:
            self._logger = logging.getLogger(self.name)
            self._logger.propagate = not self.flat
            self._logger.setLevel(self.log_level)
            if self.flat:
                self._logger.addHandler(self._get_handler())
        return self._logger

    @classmethod
    def _get_handler_factory(cls, config):
        return getattr(config, "_create_%s_handler" % config.destination)
        
    @classmethod        
    def get(cls, name):
        name = name or ""
        ret = LogConfig._configs.get(name)
        if not ret:
            ret = LogConfig(name)
            LogConfig._configs[name] = ret
        return ret
    
def get_logger(name):
    return LogConfig.get(name).get_logger()

# Tie our logging config into the platform's by pre-initializing all loggers 
# we know of. This way we can use propagate = True to combine logging across
# a package.
# 
# FIXME: I should really do this properly and have the platform logging use
# gripe.Config.
for name in filter(lambda n: n in ("__root__", "__main__") or not n.startswith("_"), Config["logging"].keys()):
    get_logger(name if name != "__root__" else "")
    
logging.basicConfig(stream = sys.stderr, 
                    level = LogConfig._default_config["level"], 
                    datefmt = LogConfig._default_config["dateformat"], 
                    format = LogConfig._default_config["format"])

if __name__ == "__main__":
    Config.backup()

