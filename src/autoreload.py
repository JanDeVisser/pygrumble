# autoreloading launcher
# stolen a lot from Ian Bicking's WSGIKit (www.wsgikit.org)

import errno
import sys
import thread
import time

import os
import re

RUN_RELOADER = True
reloadFiles = []
ignoreFiles = ['<string>']
#path = "[Cc]:\\Users\\jan\\Documents\\Projects\\Grumble"
path = ".*"
match = ".*"


def reloader_thread(freq):
    mtimes = {}

    main = sys.modules["__main__"]
    (prj_path, slash, main_py) = main.__file__.replace('\\', '/').rpartition("/")
    print prj_path, main_py

    i = 1
    while RUN_RELOADER:
        sysfiles = []


        print "autoreload - checking", i
        i += 1
        for k, m in sys.modules.items():
            f = None
            if m:
                if hasattr(m, "__loader__") and hasattr(m.__loader__, "archive"):
                    f = m.__loader__.archive
                if hasattr(m, "__file__") and m.__file__.replace('\\', '/').startswith(prj_path) and re.match(match, k):
                    f = m.__file__
                    print k, f
            sysfiles.append(f)

        print mtimes
        for filename in sysfiles + reloadFiles:
            if filename and filename not in ignoreFiles:

                orig = filename
                if filename.endswith(".pyc"):
                    filename = filename[:-1]

                # Get the last-modified time of the source file.
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError, e:
                    if orig.endswith('.pyc') and e[0] == errno.ENOENT:
                        # This prevents us from endlessly restarting if
                        # there is an old .pyc lying around after a .py
                        # file has been deleted. Note that TG's solution
                        # actually deletes the .pyc, but we just ignore it.
                        # See http://www.cherrypy.org/ticket/438.
                        continue
                    sys.exit(3) # force reload

                if filename not in mtimes:
                    mtimes[filename] = mtime
                    continue

                if mtime > mtimes[filename]:
                    print filename, "Triggered it"
                    sys.exit(3) # force reload
        time.sleep(freq)

def restart_with_reloader():
    while True:
        args = [sys.executable] + sys.argv
        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        exit_code = os.spawnve(os.P_WAIT, sys.executable, args, new_environ)
        if exit_code != 3:
            return exit_code

def main(main_func, args=None, kwargs=None, freq=1):
    if os.environ.get("RUN_MAIN") == "true":

        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        thread.start_new_thread(main_func, args, kwargs)

        # If KeyboardInterrupt is raised within reloader_thread,
        # let it propagate out to the caller.
        reloader_thread(freq)
    else:
        # If KeyboardInterrupt is raised within restart_with_reloader,
        # let it propagate out to the caller.
        sys.exit(restart_with_reloader())