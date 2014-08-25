'''
Created on Aug 16, 2014

@author: jan
'''

import base64
import math
import os.path
import sys

import sweattrails.device.ant.fs.manager

import gripe

logger = gripe.get_logger(__name__)

ID_VENDOR  = 0x0fcf
ID_PRODUCT = 0x1008

PRODUCT_NAME = "sweattrails"

class BackendBridge(object):
    def __init__(self):
        pass
        
    def get_passkey(self, serial):
        return None
        
    def set_passkey(self, serial, passkey):
        pass

    def log(self, msg, *args):
        logger.info(msg, *args)
        
    def progress_init(self, msg, *args):
        pass
    
    def progress(self, num):
        pass
        
    def progress_end(self):
        pass
        
    def exists(self, antfile):
        return False
    
    def process(self, antfile, data):
        """
            antfile - ANT-FS file structure (ant.fs.file.File)
            data - An array.array object with typecode 'b'.
        """
        pass


class GarminBridge(sweattrails.device.ant.fs.manager.Application):
    ID_VENDOR  = 0x0fcf
    ID_PRODUCT = 0x1008

    PRODUCT_NAME = "sweattrails"

    def __init__(self, bridge):
        self.bridge = bridge
        super(GarminBridge, self).__init__(bridge)
        
    def log(self, msg, *args):
        if self.bridge:
            self.bridge.log(msg, *args)

    def setup_channel(self, channel):
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)
        
        channel.open()
        #channel.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)
        self.log("Searching...")

    def on_link(self, beacon):
        logger.debug("on link, %r, %r", beacon.get_serial(), beacon.get_descriptor())
        self.link()
        return True

    def on_authentication(self, beacon):
        logger.debug("on authentication")
        self.serial, self.name = self.authentication_serial()
        self.passkey = self.bridge.get_passkey(self.serial)
        self.log("Authenticating with {} ({})...", self.name, self.serial)
        logger.debug("serial %s, %r, %r", self.name, self.serial, self.passkey)
        
        if self.passkey is not None:
            self.log("Authenticating with {} ({})... Passkey... ", self.name, self.serial)
            try:
                self.authentication_passkey(self.passkey)
                self.log("Authenticating with {} ({})... Passkey... OK.", self.name, self.serial)
                return True
            except sweattrails.device.ant.fs.manager.AntFSAuthenticationException:
                self.log("Authenticating with {} ({})... Passkey... FAILED", self.name, self.serial)
                return False
        else:
            self.log("Authenticating with {} ({})... Pairing... ", self.name, self.serial)
            try:
                self.passkey = self.authentication_pair(self.PRODUCT_NAME)
                self.bridge.set_passkey(self.serial, self.passkey)
                self.log("Authenticating with {} ({})... Pairing... OK.", self.name, self.serial)
                return True
            except sweattrails.device.ant.fs.manager.AntFSAuthenticationException:
                self.log("Authenticating with {} ({})... Pairing... FAILED", self.name, self.serial)
                return False

    def on_transport(self, beacon):
        directory = self.download_directory()
        antfiles = directory.get_files()[2:]

        downloading = filter(lambda f: not self.bridge.exists(f), antfiles)
        l = len(downloading)
        self.log("Downloading {} file{}", l, "" if l == 1 else "s")

        # Download missing files:
        for f in downloading:
            self.download_file(f)


    def download_file(self, f):
        try:
            self.bridge.progress_init("Downloading activity from {} ", f.get_date().strftime("%d %b %Y %H:%M"))
            def callback(progress):
                self.bridge.progress(int(math.floor(progress * 100.0)))
            data = self.download(f.get_index(), callback)
            self.bridge.progress_end()
            self.log("Processing activity from {} ", f.get_date().strftime("%d %b %Y %H:%M"))
            self.bridge.process(f, data)
        except:
            traceback.print_exc()


class GripeConfigBridge(BackendBridge):
    def init_config(self):
        if "garmin" not in gripe.Config:
            self.config = gripe.Config.set("garmin", {})
        else:
            self.config = gripe.Config.garmin
        
    def get_passkey(self, serial):
        self.serial = serial 
        s = str(serial)
        if s not in self.config or \
                "passkey" not in self.config[s]:
            return None
        else:
            return base64.b64decode(self.config[s]["passkey"])
        
    def set_passkey(self, serial, passkey):
        s = str(serial)
        if s not in self.config:
            self.config[s] = {}
        self.config[s]["passkey"] = base64.b64encode(passkey)
        self.config = gripe.Config.set("garmin", self.config)
    

#
# ---------------------------------------------------------------------------
#  T E S T / S T A N D A L O N E  C O D E 
# ---------------------------------------------------------------------------
#

if __name__ == "__main__":
    import traceback

    class FileBridge(GripeConfigBridge):
        def __init__(self):
            super(FileBridge, self).__init__()
            self.init_config()
            self.basedir = self.config.get("basedir", "fit")
            gripe.mkdir(self.basedir)
            
        def log(self, msg, *args):
            print msg.format(args)
            
        def progress_init(self, msg, *args):
            self.curr_progress = 0
            sys.stdout.write((msg + " [").format(*args))
            sys.stdout.flush()
            
        def progress(self, new_progress):
            diff = int((new_progress - self.curr_progress) / 10.0) 
            sys.stderr.write("." * diff)
            sys.stdout.flush()
            self.curr_progress = new_progress
            
        def progress_end(self):
            sys.stdout.write("]\n")
            sys.stdout.flush()
            
        def exists(self, antfile):
            return os.access(self.get_filepath(antfile), os.F_OK)
        
        def process(self, antfile, data):
            with open(self.get_filepath(antfile), "w") as fd:
                data.tofile(fd)
        
        def get_filename(self, antfile):
            return str.format("{0}-{1:02x}-{2}.fit",
                    antfile.get_date().strftime("%Y-%m-%d_%H-%M-%S"),
                    antfile.get_type(), antfile.get_size())
    
        def get_filepath(self, antfile):
            return os.path.join(self.basedir, str(self.serial),
                    "fit", self.get_filename(antfile))
    
    
    def main():    
        try:
            fb = FileBridge()
            g = GarminBridge(fb)
            g.start()
        except (Exception, KeyboardInterrupt):
            traceback.print_exc()
            print "Interrupted"
            g.stop()
            sys.exit(1)

    sys.exit(main())
