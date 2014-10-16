# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import sys
import socket
from collections import deque
import greenlet
from tornado.ioloop import IOLoop
from stream import TStream

class StreamCloseError(Exception):pass

class TStream(TStream):
    def __init__(self, *args, **kwargs):
        super(TStream, self).__init__(*args, **kwargs)

        self.run_gr = None

    def open(self):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        super(TStream, self).open(lambda :child_gr.switch())
        return main.switch()

    def acquire_stream(self):
        self.run_gr = greenlet.getcurrent()

    def release_stream(self):
        self.run_gr = None

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

    def close_stream(self, stream):
        try:
            self._used_streams.remove(stream)
            self._stream_count -= 1
        except ValueError:
            try:
                self._streams.remove(stream)
                self._stream_count -= 1
            except ValueError:
                pass
        if stream.run_gr:
            IOLoop.current().add_callback(lambda :stream.run_gr.throw(StreamCloseError("stream close")))

    def init_stream(self):
        stream = TStream(self._host, self._port, self._unix_socket, self._socket_family)
        stream.set_close_callback(lambda :self.close_stream(stream))
        self._used_streams.append(stream)
        self._stream_count += 1
        stream.open()
        return stream

    def get_stream(self):
        if self._streams:
            stream = self._streams.popleft()
        else:
            if self._stream_count < self._max_stream:
                stream = self.init_stream()
            else:
                child_gr = greenlet.getcurrent()
                main = child_gr.parent
                self._wait_streams.append(child_gr)
                stream = main.switch()
        stream.acquire_stream()
        return stream

    def release_stream(self, stream):
        stream.release_stream()
        if self._wait_streams:
            child_gr = self._wait_streams.popleft()
            IOLoop.current().add_callback(lambda :child_gr.switch(stream))
        else:
            try:
                self._used_streams.remove(stream)
            except ValueError:
                pass
            self._streams.append(stream)
