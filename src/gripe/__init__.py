__author__ = "jan"
__date__ = "$18-Feb-2013 11:06:29 AM$"

import importlib
import json
import logging
import os
import os.path
import sys
import threading

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
        logging.info("root dir: %s", _root_dir)
    return _root_dir
#       logging.info("os.getcwd(): %s", os.getcwd())
#   return os.getcwd()


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


def resolve(funcname, default = None):
    if funcname:
        if callable(funcname):
            return funcname
        try:
            (module, dot, fnc) = funcname.rpartition(".")
            logger.debug("resolve(%s): Importing module %s and getting function %s", funcname, module, fnc)
            mod = importlib.import_module(module)
            return getattr(mod, fnc) if hasattr(mod, fnc) and callable(getattr(mod, fnc)) else default
        except Exception, exc:
            logger.error("Exception in gripe.resolve(%s): %s %s", funcname, exc.__class__.__name__, exc)
            raise
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
        if name == "_sections":
            return super(ConfigMeta, cls).__getattribute__("_sections")
        if not super(ConfigMeta, cls).__getattribute__("_loaded"):
            super(ConfigMeta, cls).__getattribute__("_load")()
        return super(ConfigMeta, cls).__getattribute__(name)
    
    def __setattr__(cls, name, value):
        cls._sections.add(name)
        return super(ConfigMeta, cls).__setattr__(name, value)
     
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
    def set(cls, section, config):
        config = gripe.json_util.JSONObject(config) \
            if not isinstance(config, gripe.json_util.JSONObject) \
            else config
        if (not os.access("%s/conf/%s.json.backup" % (root_dir(), section), os.F_OK) and
                os.access("%s/conf/%s.json" % (root_dir(), section), os.F_OK)):
            print "Renaming conf/%s.json to conf/%s.json.backup" % (section, section)
            os.rename(os.path.join(root_dir(), "conf/%s.json" % section), os.path.join(root_dir(), "conf/%s.json.backup" % section))
        config.file_write("conf/%s.json" % section, 4)
        setattr(cls, section, config)

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
                # print >> sys.stderr, "Config.%s: %s" % (section, json.dumps(config))
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

_loggers = {}
_log_defaults = None
_log_date_fmt = '%y%m%d %H:%M:%S'
_log_root_fmt = '%(name)-15s:%(asctime)s:%(levelname)-7s:%(message)s'
_log_sub_fmt = '%(name)-15s:%(asctime)s:%(levelname)-7s:%(message)s'

class LogConfig(object):
    def __init__(self, conf = None, defaults = None):
        conf = conf or object()
        self.log_level = defaults.log_level if defaults else logging.INFO
        self.log_level = getattr(logging, conf.level.upper()) if hasattr(conf, "level") and conf.level else self.log_level
        self.destination = defaults.destination if defaults else "stderr"
        self.destination = conf.destination.lower() if hasattr(conf, "destination") and conf.destination else self.destination
        assert self.destination in ("stderr", "file"), "Invalid logging destination %s" % self.destination
        self.flat = defaults.flat if defaults else False
        self.flat = conf.flat if hasattr(conf, "flat") else self.flat
        self.append = defaults.append if defaults else False
        self.append = conf.append if hasattr(conf, "append") else self.append

def get_logger(name):
    global _log_defaults
    global _loggers

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    assert logger, "logging.getLogger(%s) returned None" % name
    logger.propagate = False
    formatter = logging.Formatter(_log_sub_fmt, _log_date_fmt)
    conf = LogConfig(Config.logging[name] if hasattr(Config, "logging") and name in Config.logging else None, _log_defaults)
    logger.setLevel(conf.log_level)
    if "file" in conf.destination:
        try:
            os.mkdir("%s/logs" % root_dir())
        except:
            # Ignored. Probably already exists
            pass
        append = conf.append if conf.append is not None else False
        mode = "a" if append else "w"
        if conf.flat:
            (fname, _, _) = name.partition(".")
        else:
            fname = name
        # fh = logging.FileHandler("%s/logs/%s.log" % (root_dir(), name), mode)
        fh = logging.FileHandler("%s/logs/%s.log" % (root_dir(), fname))
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    else:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    _loggers[name] = logger
    return logger

_log_defaults = LogConfig(Config.logging if hasattr(Config, "logging") else None)
logging.basicConfig(stream = sys.stderr, level = _log_defaults.log_level, datefmt = _log_date_fmt, format = _log_root_fmt)
logger = get_logger(__name__)
