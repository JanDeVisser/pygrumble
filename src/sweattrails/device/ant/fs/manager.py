# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#               2014, Jan de Visser <jan@ssweattrails.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import struct
import threading
import Queue

import sweattrails.device.ant.fs.command

from sweattrails.device.ant.easy.channel import Channel
from sweattrails.device.ant.easy.node import Message
from sweattrails.device.ant.easy.node import Node
from sweattrails.device.ant.fs.beacon import Beacon
from sweattrails.device.ant.fs.command import AuthenticateCommand
from sweattrails.device.ant.fs.command import AuthenticateResponse
from sweattrails.device.ant.fs.command import DisconnectCommand
from sweattrails.device.ant.fs.command import DownloadRequest
from sweattrails.device.ant.fs.command import DownloadResponse
from sweattrails.device.ant.fs.command import LinkCommand
from sweattrails.device.ant.fs.command import PingCommand
from sweattrails.device.ant.fs.file import Directory

import gripe

_logger = gripe.get_logger(__name__)
debug_protocol = False

class AntFSException(Exception):
    pass

class AntFSDownloadException(AntFSException):
    
    def __init__(self, error):
        self.error = error

class AntFSAuthenticationException(AntFSException):
    
    def __init__(self, error):
        self.error = error

class Application(object):
    
    _serial_number = 1337
    _frequency     = 19    # 0 to 124, x - 2400 (in MHz)
    
    def __init__(self, logger, **kwargs):
        _logger.debug("Application __init__")
        self.logger = logger
        self.logger.log("Initializing ANT-FS Application")
        
        self.keep_alive = kwargs.get("keep_alive", True)
        self._timer = None
        if self.keep_alive:
            self._timer_lock = threading.RLock()

        self._lock = threading.RLock()
        self._queue = Queue.Queue()
        self._beacons = Queue.Queue()

        self._node = Node(0x0fcf, 0x1008)
        _logger.debug("Application: Node initialized")

        self.logger.log("Request basic information...")
        m = self._node.request_message(Message.ID.RESPONSE_VERSION)
        self.logger.log("  ANT version:   {}", struct.unpack("<10sx", m[2])[0])
        m = self._node.request_message(Message.ID.RESPONSE_CAPABILITIES)
        self.logger.log("  Capabilities:  {}", m[2])
        m = self._node.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
        self.logger.log("  Serial number: {}", struct.unpack("<I", m[2])[0])
        _logger.debug("Application: retrieved basic info")

        self.logger.log("Starting system...")

        NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]

        self._node.reset_system()
        self._node.set_network_key(0x00, NETWORK_KEY)
        _logger.debug("Application: Node initialized")

        self._channel = self._node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        self._channel.on_broadcast_data = self._on_data
        self._channel.on_burst_data = self._on_data
        _logger.debug("Application: New channel created")
        
        self.setup_channel(self._channel)
        _logger.debug("Application: New channel initialized")
        
        self._worker_thread = threading.Thread(target=self._worker, name="ant.fs")
        self._worker_thread.start()
        _logger.debug("Application: Thread created and started")

    def _worker(self):
        self._node.start()

    def _main(self):
        try:
            _logger.debug("Link level")
            beacon = self._get_beacon()
            if self.on_link(beacon):
                for _ in range(0, 5):
                    beacon = self._get_beacon()
                    if beacon.get_client_device_state() == Beacon.ClientDeviceState.AUTHENTICATION:
                        _logger.debug("Auth layer")
                        if self.on_authentication(beacon):
                            _logger.debug("Authenticated")
                            beacon = self._get_beacon()
                            self._keep_alive(False)
                            try:
                                self.on_transport(beacon)
                            finally:
                                self._cancel_keep_alive()
                        self.disconnect()
                        break
        except:
            _logger.exception("Exception in ANT manager main loop")
            raise
        finally:
            self.stop()

    def _on_beacon(self, data):
        b = Beacon.parse(data)
        self._beacons.put(b)

    def _on_command(self, data):
        c = sweattrails.device.ant.fs.command.parse(data)
        self._queue.put(c)

    def _on_data(self, data):
        #print "_on_data", data, len(data)
        if data[0] == 0x43:
            self._on_beacon(data[:8])
            if len(data[8:]) > 0:
                self._on_command(data[8:])
        elif data[0] == 0x44:
            self._on_command(data)
    
    def _get_beacon(self):
        b = self._beacons.get()
        self._beacons.task_done()
        return b
    
    def _get_command(self, timeout=3.0):
        _logger.debug("Get command, t%d, s%d", timeout, self._queue.qsize())
        c = self._queue.get(True, timeout)
        self._queue.task_done()
        return c
    
    def _send_command(self, c):
        _logger.debug("Sending '%s' command", c.__class__.__name__)
        data = c.get()
        if len(data) <= 8:
            self._channel.send_acknowledged_data(data)
        else:
            self._channel.send_burst_transfer(data)
            
    def _keep_alive(self, ping_now = True):
        if self.keep_alive:
            _logger.debug("Sending keep-alive Ping command")
            with self._timer_lock:
                self._timer = None
                if ping_now:
                    self.ping()
                self._timer = threading.Timer(1, self._keep_alive)
                self._timer.start()
            _logger.debug("Keep-alive Ping succeeded")
        
    def _cancel_keep_alive(self):
        if self.keep_alive:
            _logger.debug("Canceling keep-alive timer")
            with self._timer_lock:
                if self._timer:
                    self._timer.cancel()
                    self._timer = None
    
    # Application actions are defined from here
    # =======================================================================
    
    # These should be overloaded:
    
    def setup_channel(self, channel):
        pass
    
    def on_link(self, beacon):
        pass
    
    def on_authentication(self, beacon):
        pass
    
    def on_transport(self, beacon):
        pass
    
    # Shouldn't have to touch these:
    
    def start(self):
        self._main()

    def stop(self):
        self._node.stop()
    
    def erase(self, index):
        pass
    
    def upload(self, index, data):
        pass
    
    def download(self, index, callback = None):
        offset  = 0
        initial = True
        crc     = 0
        data    = array.array('B')
        with self._lock:
            while True:
                _logger.debug("Download %d, o%d, c%d", index, offset, crc)
                self._send_command(DownloadRequest(index, offset, True, crc))
                _logger.debug("Wait for response...")
                try:
                    response = self._get_command()
                    if response._get_argument("response") == DownloadResponse.Response.OK:
                        _logger.debug("Response OK")
                        remaining    = response._get_argument("remaining")
                        offset       = response._get_argument("offset")
                        total        = offset + remaining
                        size         = response._get_argument("size")
                        if debug_protocol:
                            _logger.debug("remaining %d offset %d total %d size %d", remaining, offset, total, response._get_argument("size"))
                        data[offset:total] = response._get_argument("data")[:remaining]
                        if callback != None:
                            callback(float(total) / float(response._get_argument("size")))
                        if total == size:
                            return data
                        crc = response._get_argument("crc")
                        if debug_protocol:
                            _logger.debug("crc: %d", crc)
                        offset = total
                    else:
                        raise AntFSDownloadException(response._get_argument("response"))
                except Queue.Empty:
                    _logger.debug("Download %d timeout", index)
                except AntFSException:
                    raise
                except:
                    _logger.exception("Exception in download. Attempting to recover...")
    
    def download_directory(self, callback = None):
        data = self.download(0, callback)
        return Directory.parse(data)
    
    def ping(self):
        """
            Pings the device. Used by the keep-alive thread.
        """
        with self._lock:
            self._send_command(PingCommand())

    def link(self):
        with self._lock:
            self._channel.request_message(Message.ID.RESPONSE_CHANNEL_ID)
            self._send_command(LinkCommand(self._frequency, 4, self._serial_number))
           
            # New period, search timeout
            self._channel.set_period(4096)
            self._channel.set_search_timeout(3)
            self._channel.set_rf_freq(self._frequency)

    def authentication_serial(self):
        with self._lock:
            self._send_command(AuthenticateCommand(
                    AuthenticateCommand.Request.SERIAL,
                    self._serial_number))
            response = self._get_command()
            return (response.get_serial(), response.get_data_string())

    def authentication_passkey(self, passkey):
        with self._lock:
            self._send_command(AuthenticateCommand(
                    AuthenticateCommand.Request.PASSKEY_EXCHANGE,
                    self._serial_number, passkey))
    
            response = self._get_command()
            if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
                return response.get_data_array()
            else:
                raise AntFSAuthenticationException(response._get_argument("type"))

    def authentication_pair(self, friendly_name):
        with self._lock:
            data = array.array('B', map(ord, list(friendly_name)))
            self._send_command(AuthenticateCommand(
                    AuthenticateCommand.Request.PAIRING,
                    self._serial_number, data))
    
            response = self._get_command(30)
            if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
                return response.get_data_array()
            else:
                raise AntFSAuthenticationException(response._get_argument("type"))

    def disconnect(self):
        with self._lock:
            d = DisconnectCommand(DisconnectCommand.Type.RETURN_LINK, 0, 0)
            self._send_command(d)

