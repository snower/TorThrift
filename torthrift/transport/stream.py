# -*- coding: utf-8 -*-
# 14-8-16
# create by: snower

import sys
import time
import socket
import errno
from tornado.concurrent import Future
from tornado.iostream import IOStream, StreamClosedError, _ERRNO_WOULDBLOCK


class TStreamConnectTimeoutError(Exception):
    pass


class TStream(IOStream):
    def __init__(self, host='127.0.0.1', port=9090, unix_socket=None, socket_family=socket.AF_UNSPEC, timeout=5):
        self._host = host
        self._port = port
        self._unix_socket = unix_socket
        self._socket_family = socket_family
        self._timeout = timeout
        self._write_future = None

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
        try:
            future = self.connect(address)
            if self._timeout > 0:
                def timeout():
                    if self._connecting:
                        self.close((None, TStreamConnectTimeoutError(), None))

                self.io_loop.add_timeout(time.time() + self._timeout, timeout)
        except Exception:
            future = Future()
            future.set_exc_info(sys.exc_info())
        return future

    def _handle_events(self, fd, events):
        if self._closed:
            return
        try:
            if self._connecting:
                self._handle_connect()
            if self._closed:
                return
            if events & self.io_loop.READ:
                self._handle_read()
            if self._closed:
                return
            if events & self.io_loop.WRITE:
                self._handle_write()
            if self._closed:
                return
            if events & self.io_loop.ERROR:
                self.error = self.get_fd_error()
                self.io_loop.add_callback(self.close)
                return
        except Exception:
            self.close(exc_info=True)
            raise

    def _handle_connect(self):
        super(TStream, self)._handle_connect()

        if not self.closed():
            self._state = self.io_loop.ERROR | self.io_loop.READ
            if self._write_buffer:
                self._state = self._state | self.io_loop.WRITE
            self.io_loop.update_handler(self.fileno(), self._state)

    def _handle_read(self):
        chunk = True

        while True:
            try:
                chunk = self.socket.recv(self.read_chunk_size)
                if not chunk:
                    break
                if self._read_buffer_size:
                    self._read_buffer += chunk
                else:
                    self._read_buffer = bytearray(chunk)
                self._read_buffer_size += len(chunk)
            except (socket.error, IOError, OSError) as e:
                en = e.errno if hasattr(e, 'errno') else e.args[0]
                if en in _ERRNO_WOULDBLOCK:
                    break

                if en == errno.EINTR:
                    continue

                self.close(exc_info=True)
                return

        if self._read_future is not None and self._read_buffer_size >= self._read_bytes:
            future, self._read_future = self._read_future, None
            self._read_buffer, data = bytearray(), self._read_buffer
            self._read_buffer_size = 0
            self._read_bytes = 0
            future.set_result(data)

        if not chunk:
            self.close()
            return

    def read(self, num_bytes):
        assert self._read_future is None, "Already reading"
        if self._closed:
            raise StreamClosedError(real_error=self.error)

        future = self._read_future = Future()
        self._read_bytes = num_bytes
        self._read_partial = False
        if self._read_buffer_size >= self._read_bytes:
            future, self._read_future = self._read_future, None
            self._read_buffer, data = bytearray(), self._read_buffer
            self._read_buffer_size = 0
            self._read_bytes = 0
            future.set_result(data)
        return future

    def _handle_write(self):
        try:
            num_bytes = self.socket.send(memoryview(self._write_buffer)[
                                         self._write_buffer_pos: self._write_buffer_pos + self._write_buffer_size])
            self._write_buffer_pos += num_bytes
            self._write_buffer_size -= num_bytes
        except (socket.error, IOError, OSError) as e:
            en = e.errno if hasattr(e, 'errno') else e.args[0]
            if en not in _ERRNO_WOULDBLOCK:
                self.close(exc_info=True)
                return

        if not self._write_buffer_size:
            if self._write_buffer_pos > 0:
                self._write_buffer = bytearray()
                self._write_buffer_pos = 0

            if self._state & self.io_loop.WRITE:
                self._state = self._state & ~self.io_loop.WRITE
                self.io_loop.update_handler(self.fileno(), self._state)
            if self._write_future:
                future, self._write_future = self._write_future, None
                future.set_result(None)

    def write(self, data):
        assert isinstance(data, bytes)
        if self._closed:
            raise StreamClosedError(real_error=self.error)

        if not data:
            if self._write_future:
                return self._write_future
            future = Future()
            future.set_result(None)
            return future

        if self._write_buffer_size:
            self._write_buffer += data
        else:
            self._write_buffer = bytearray(data)
        self._write_buffer_size += len(data)
        future = self._write_future = Future()

        if not self._connecting:
            self._handle_write()
            if self._write_buffer_size:
                if not self._state & self.io_loop.WRITE:
                    self._state = self._state | self.io_loop.WRITE
                    self.io_loop.update_handler(self.fileno(), self._state)

        return future