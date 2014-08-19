# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import sys
import socket
from collections import deque
import greenlet
from tornado.ioloop import IOLoop
from stream import TStream

class TStream(TStream):
    def open(self):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        super(TStream, self).open(lambda :child_gr.switch())
        return main.switch()

class TStreamPool(object):
    def __init__(self, host='127.0.0.1', port=9090, unix_socket=None, max_stream=4, socket_family=socket.AF_UNSPEC):
        self._host = host
        self._port = port
        self._unix_socket = unix_socket
        self._max_stream = max_stream
        self._socket_family = socket_family
        self._streams = deque()
        self._used_streams = deque()
        self._stream_count = 0
        self._wait_streams = deque()

    def init_stream(self):
        stream = TStream(self._host, self._port, self._unix_socket, self._socket_family)
        def on_close():
            try:
                self._used_streams.remove(stream)
            except ValueError:
                try:
                    self._streams.remove(stream)
                except ValueError:
                    return
            self._stream_count -= 1
        stream.set_close_callback(on_close)
        self._used_streams.append(stream)
        self._stream_count += 1
        stream.open()
        return stream

    def get_stream(self):
        if self._streams:
            return self._streams.popleft()
        else:
            if self._stream_count < self._max_stream:
                return self.init_stream()
            else:
                child_gr = greenlet.getcurrent()
                main = child_gr.parent
                self._wait_streams.append(child_gr)
                return main.switch()

    def release_stream(self, stream):
        if self._wait_streams:
            child_gr = self._wait_streams.popleft()
            IOLoop.current().add_callback(lambda :child_gr.switch(stream))
        else:
            try:
                self._used_streams.remove(stream)
            except ValueError:
                pass
            self._streams.append(stream)
