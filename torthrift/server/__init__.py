# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
import logging
import socket
import errno
import ssl
import greenlet
from tornado import tcpserver
from tornado.concurrent import TracebackFuture
from tornado.tcpserver import ssl_wrap_socket, app_log
from tornado.iostream import IOStream as BaseIOStream, SSLIOStream, StreamClosedError, errno_from_exception, _ERRNO_WOULDBLOCK
from .handler import HandlerWrapper

class IOStream(BaseIOStream):
    def __init__(self, socket, *args, **kwargs):
        super(IOStream, self).__init__(socket, *args, **kwargs)

        if socket and self._state is None:
            self._state = self.io_loop.ERROR | self.io_loop.READ
            self.io_loop.add_handler(self.fileno(), self._handle_events, self._state)

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

    def _handle_read(self):
        chunk = True

        while True:
            try:
                chunk = self.socket.recv(self.read_chunk_size)
                if not chunk:
                    break
                self._read_buffer.append(chunk)
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
            data = b"".join(self._read_buffer)
            self._read_buffer.clear()
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

        future = self._read_future = TracebackFuture()
        self._read_bytes = num_bytes
        self._read_partial = False
        if self._read_buffer_size >= self._read_bytes:
            future, self._read_future = self._read_future, None
            data = b"".join(self._read_buffer)
            self._read_buffer.clear()
            self._read_buffer_size = 0
            self._read_bytes = 0
            future.set_result(data)
        return future

    def _handle_write(self):
        while self._write_buffer:
            try:
                data = self._write_buffer.popleft()
                num_bytes = self.socket.send(data)
                self._write_buffer_size -= num_bytes
                if num_bytes < len(data):
                    self._write_buffer.appendleft(data[num_bytes:])
                    return
            except (socket.error, IOError, OSError) as e:
                en = e.errno if hasattr(e, 'errno') else e.args[0]
                if en in _ERRNO_WOULDBLOCK:
                    self._write_buffer.appendleft(data)
                    break

                self.close(exc_info=True)
                return

        if not self._write_buffer:
            if self._state & self.io_loop.WRITE:
                self._state = self._state & ~self.io_loop.WRITE
                self.io_loop.update_handler(self.fileno(), self._state)

    def write(self, data):
        assert isinstance(data, bytes)
        if self._closed:
            raise StreamClosedError(real_error=self.error)

        if data:
            self._write_buffer.append(data)
            self._write_buffer_size += len(data)

        if not self._connecting:
            self._handle_write()
            if self._write_buffer:
                if not self._state & self.io_loop.WRITE:
                    self._state = self._state | self.io_loop.WRITE
                    self.io_loop.update_handler(self.fileno(), self._state)

class TTornadoServer(tcpserver.TCPServer):
    def __init__(self, processor, input_transport_factory, input_protocol_factory, output_transport_factory = None, output_protocol_factory = None, *args, **kwargs):
        super(TTornadoServer,self).__init__(*args, **kwargs)

        self.processor = processor
        self.input_transport_factory = input_transport_factory
        self.output_transport_factory = output_transport_factory
        self.input_protocol_factory = input_protocol_factory
        self.output_protocol_factory = output_protocol_factory

        self.processor._handler = HandlerWrapper(self.processor, self.processor._handler)

    def handle_exception(self, exec_info):
        logging.error("processor error: %s", exec_info = exec_info)

    def process(self, itrans, otrans):
        iprot = self.input_protocol_factory.getProtocol(itrans)
        oprot = self.output_protocol_factory.getProtocol(otrans) if otrans and self.output_protocol_factory else iprot
        while True:
            try:
                self.processor.process(iprot, oprot)
            except (IOError, StreamClosedError, EOFError):
                itrans.close()
                if otrans:
                    otrans.close()
                break
            except Exception:
                exc_info = sys.exc_info()
                itrans.close()
                if otrans:
                    otrans.close()
                self.handle_exception(exc_info)
                break

    def _handle_connection(self, connection, address):
        if self.ssl_options is not None:
            assert ssl, "Python 2.6+ and OpenSSL required for SSL"
            try:
                connection = ssl_wrap_socket(connection,
                                             self.ssl_options,
                                             server_side=True,
                                             do_handshake_on_connect=False)
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    return connection.close()
                else:
                    raise
            except socket.error as err:
                if errno_from_exception(err) in (errno.ECONNABORTED, errno.EINVAL):
                    return connection.close()
                else:
                    raise
        try:
            if self.ssl_options is not None:
                stream = SSLIOStream(connection, io_loop=self.io_loop,
                                     max_buffer_size=self.max_buffer_size,
                                     read_chunk_size=self.read_chunk_size)
            else:
                stream = IOStream(connection, io_loop=self.io_loop,
                                  max_buffer_size=self.max_buffer_size,
                                  read_chunk_size=self.read_chunk_size)
            self.handle_stream(stream, address)
        except Exception:
            self.handle_exception(sys.exc_info())

    def handle_stream(self, stream, address):
        itrans = self.input_transport_factory.getTransport(stream)
        otrans = self.output_transport_factory.getTransport(stream) if self.output_transport_factory else None
        child_gr = greenlet.greenlet(self.process)
        child_gr.switch(itrans, otrans)