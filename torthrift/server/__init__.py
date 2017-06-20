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
from tornado.concurrent import Future
from tornado.tcpserver import ssl_wrap_socket
from tornado.iostream import IOStream as BaseIOStream, SSLIOStream, StreamClosedError, errno_from_exception, _ERRNO_WOULDBLOCK
from thrift.transport import TTransport
from .handler import HandlerWrapper


class IOStream(BaseIOStream):
    def __init__(self, socket, *args, **kwargs):
        super(IOStream, self).__init__(socket, *args, **kwargs)

        self._write_future = None

        if socket and self._state is None:
            self._state = self.io_loop.ERROR | self.io_loop.READ
            self.io_loop.add_handler(self.fileno(), self._handle_events, self._state)

    def _handle_events(self, fd, events):
        if self._closed:
            return
        try:
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

        self._handle_write()
        if self._write_buffer_size:
            if not self._state & self.io_loop.WRITE:
                self._state = self._state | self.io_loop.WRITE
                self.io_loop.update_handler(self.fileno(), self._state)

        return future


class TTornadoServer(tcpserver.TCPServer):
    def __init__(self, processor, input_transport_factory, input_protocol_factory, output_transport_factory = None, output_protocol_factory = None, *args, **kwargs):
        super(TTornadoServer,self).__init__(*args, **kwargs)

        self.processor = processor
        self.processor_count = 0
        self.handing_count = 0
        self.stoped = False
        self.input_transport_factory = input_transport_factory
        self.output_transport_factory = output_transport_factory
        self.input_protocol_factory = input_protocol_factory
        self.output_protocol_factory = output_protocol_factory

        self.processor._handler = HandlerWrapper(self, self.processor, self.processor._handler)

    def handle_exception(self, exc_info):
        logging.error("processor error: %s", exc_info = exc_info)

    def process(self, itrans, otrans):
        iprot = self.input_protocol_factory.getProtocol(itrans)
        oprot = self.output_protocol_factory.getProtocol(otrans) if otrans and self.output_protocol_factory else iprot

        try:
            self.processor_count += 1
            while not self.stoped:
                self.processor.process(iprot, oprot)
        except (TTransport.TTransportException, IOError, StreamClosedError, EOFError):
            pass
        except Exception:
            self.handle_exception(sys.exc_info())
        finally:
            self.processor_count -= 1

        itrans.close()
        if otrans:
            otrans.close()
        if self.handing_count == 0 and self.stoped:
            stoped_future, self.stoped = self.stoped, None
            stoped_future.set_result(None)

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

    def stop(self):
        super(TTornadoServer, self).stop()

        future = self.stoped = Future()
        if self.handing_count <= 1:
            self.stoped = None
            future.set_result(None)
        return future