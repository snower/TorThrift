# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
import greenlet
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop
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


class TIOStreamTransport(TTransport.TTransportBase):
    DEFAULT_BUFFER = 4096

    def __init__(self, stream):
        self._stream = stream
        self._wbuffer = StringIO()
        self._rbuffer = StringIO(b'')
        self._wbuffer_size = 0
        self._rbuffer_size = 0
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

    def read(self, sz):
        if sz <= self._rbuffer_size:
            self._rbuffer_size -= sz
            return self._rbuffer.read(sz)

        if sz <= self._stream._read_buffer_size + self._rbuffer_size:
            last_buf = b''
            if self._rbuffer_size > 0:
                last_buf += self._rbuffer.read()
            self._rbuffer_size = self._stream._read_buffer_size + self._rbuffer_size - sz
            self._rbuffer = StringIO(last_buf + b''.join(self._stream._read_buffer))
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
            last_buf = b''
            if self._rbuffer_size > 0:
                last_buf += self._rbuffer.read()
            self._rbuffer_size = 0
            return child_gr.switch(last_buf + data)
        future = self._stream.read_bytes(sz - self._rbuffer_size)
        self._loop.add_future(future, read_callback)
        return main.switch()

    def write(self, data):
        self._wbuffer.write(data)
        self._wbuffer_size += len(data)
        if self._wbuffer_size >= self.DEFAULT_BUFFER:
            self.flush()

    def flush(self):
        if self._wbuffer_size > 0:
            data = self._wbuffer.getvalue()
            self._wbuffer = StringIO()
            self._wbuffer_size = 0
            self._stream.write(data)