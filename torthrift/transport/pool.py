# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import sys
import socket
from collections import deque
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop
from stream import TStream

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

    def init_stream(self, future):
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
        stream.open(lambda :future.set_result(stream))
        self._stream_count += 1


    def get_stream(self):
        future = TracebackFuture()
        if self._streams:
            stream = self._streams.popleft()
            future.set_result(stream)
        else:
            if self._stream_count < self._max_stream:
                try:
                    self.init_stream(future)
                except Exception:
                    future.set_exc_info(sys.exc_info())
            else:
                self._wait_streams.append(future)
        return future

    def release_stream(self, stream):
        if self._wait_streams:
            future = self._wait_streams.popleft()
            IOLoop.current().add_callback(lambda :future.set_result(stream))
        else:
            try:
                self._used_streams.remove(stream)
            except ValueError:
                pass
            self._streams.append(stream)
