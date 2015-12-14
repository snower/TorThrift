# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
import greenlet
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from thrift.transport import TTransport

if sys.version_info[0] >= 3:
    import io
    StringIO = io.BytesIO
else:
    import cStringIO
    StringIO = cStringIO.StringIO


class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        return TIOStreamTransport(stream)


class TIOStreamTransport(TTransport.TTransportBase, TTransport.CReadableTransport):
    DEFAULT_BUFFER = 4096

    def __init__(self, stream):
        self._stream = stream
        self._wbuffer = StringIO()
        self._rbuffer = StringIO(b'')
        self._loop = IOLoop.current()

    def open(self):
        try:
            future = self._stream.open()
        except:
            exc_info = sys.exc_info()
            future = TracebackFuture()
            future.set_exc_info(exc_info)
        return future

    def closed(self):
        return self._stream.closed()

    def close(self):
        if not self.closed():
            return self._stream.close()

    def readAll(self, sz):
        try:
            return self.read(sz)
        except StreamClosedError:
            raise EOFError()

    def read(self, sz):
        data = self._rbuffer.read(sz)
        if len(data) >= sz:
            return data
        partialread = data

        if sz <= self._stream._read_buffer_size + len(partialread):
            self._rbuffer = StringIO(partialread + b''.join(self._stream._read_buffer))
            self._stream._read_buffer.clear()
            self._stream._read_buffer_size = 0
            return self._rbuffer.read(sz)

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def read_callback(future):
            if future._exc_info is not None:
                return child_gr.throw(future.exception())

            data = future.result()

            if self._stream._read_buffer_size > 0:
                self._rbuffer = StringIO(b''.join(self._stream._read_buffer))
                self._stream._read_buffer.clear()
                self._stream._read_buffer_size = 0

                if self._stream._state and (self._stream._state & self._stream.io_loop.READ == 0):
                    self._stream._state |= self._stream.io_loop.READ
                    self._stream.io_loop.update_handler(self._stream.fileno(), self._stream._state)

            return child_gr.switch(partialread + data)
        future = self._stream.read_bytes(sz - len(partialread))
        self._loop.add_future(future, read_callback)
        return main.switch()

    def write(self, data):
        self._wbuffer.write(data)

    def flush(self):
        data = self._wbuffer.getvalue()
        if data:
            self._stream.write(data)
        self._wbuffer = StringIO()

    @property
    def cstringio_buf(self):
        return self._rbuffer

    def cstringio_refill(self, partialread, reqlen):
        if reqlen <= self._stream._read_buffer_size + len(partialread):
            self._rbuffer = StringIO(partialread + b''.join(self._stream._read_buffer))
            self._stream._read_buffer.clear()
            self._stream._read_buffer_size = 0
            return self._rbuffer

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def read_callback(future):
            if future._exc_info is not None:
                return child_gr.throw(future.exception())

            data = future.result()

            if self._stream._read_buffer_size > 0:
                self._rbuffer = StringIO("".join([partialread, data, b''.join(self._stream._read_buffer)]))
                self._stream._read_buffer.clear()
                self._stream._read_buffer_size = 0

                if self._stream._state and (self._stream._state & self._stream.io_loop.READ == 0):
                    self._stream._state |= self._stream.io_loop.READ
                    self._stream.io_loop.update_handler(self._stream.fileno(), self._stream._state)
            else:
                self._rbuffer = StringIO(partialread + data)

            return child_gr.switch(self._rbuffer)
        future = self._stream.read_bytes(reqlen - len(partialread))
        self._loop.add_future(future, read_callback)
        return main.switch()