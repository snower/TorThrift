# -*- coding: utf-8 -*-
# 14-8-16
# create by: snower

import time
import socket
from tornado.iostream import IOStream

class TStreamConnectTimeoutError(Exception): pass

class TStream(IOStream):
    def __init__(self, host='127.0.0.1', port=9090, unix_socket=None, socket_family=socket.AF_UNSPEC, timeout=5):
        self._host = host
        self._port = port
        self._unix_socket = unix_socket
        self._socket_family = socket_family
        self._timeout = timeout

        if self._unix_socket:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        super(TStream, self).__init__(sock)

    def open(self):
        if self._unix_socket:
            address = self._unix_socket
        else:
            address = (self._host, self._port)
        future = self.connect(address)
        if self._timeout > 0:
            def timeout():
                if self._connecting:
                    self.close((None, TStreamConnectTimeoutError(), None))
            self.io_loop.add_timeout(time.time() + self._timeout, timeout)
        return future