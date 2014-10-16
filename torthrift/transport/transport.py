# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
import cStringIO
import greenlet
from tornado.concurrent import TracebackFuture
from thrift.transport import TTransport

class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        return TIOStreamTransport(stream)


class TIOStreamTransport(TTransport.TTransportBase):
    DEFAULT_BUFFER = 4096

    def __init__(self, stream):
        self._stream = stream
        self._wbuffer = cStringIO.StringIO()
        self._rbuffer = cStringIO.StringIO('')
        self._wbuffer_size = 0
        self._rbuffer_size = 0

    def open(self):
        future = TracebackFuture()
        try:
            self._stream.open(lambda :future.set_result(None))
        except Exception:
            future.set_exc_info(sys.exc_info())
        return future

    def isOpen(self):
        return not self._stream.closed()

    def close(self):
        return self._stream.close()

    def read(self, sz, callback):
        if sz <= self._rbuffer_size:
            self._rbuffer_size -= sz
            callback(self._rbuffer.read(sz))
        elif sz <= self._stream._read_buffer_size:
            self._rbuffer_size = self._stream._read_buffer_size - sz
            self._rbuffer = cStringIO.StringIO("".join(self._stream._read_buffer))
            self._stream._read_buffer.clear()
            self._stream._read_buffer_size = 0
            callback(self._rbuffer.read(sz))
        else:
            self._stream.read_bytes(sz,callback)

    def write(self, data):
        self._wbuffer.write(data)
        self._wbuffer_size += len(data)
        if self._wbuffer_size > self.DEFAULT_BUFFER:
            self.flush()

    def flush(self):
        if self._wbuffer_size > 0:
            data = self._wbuffer.getvalue()
            self._wbuffer = cStringIO.StringIO()
            self._wbuffer_size = 0
            self._stream.write(data)

class TGrIOStreamTransport(TIOStreamTransport):
    def read(self, sz):
        if sz <= self._rbuffer_size:
            self._rbuffer_size -= sz
            return self._rbuffer.read(sz)
        if sz <= self._stream._read_buffer_size:
            self._rbuffer_size = self._stream._read_buffer_size - sz
            self._rbuffer = cStringIO.StringIO("".join(self._stream._read_buffer))
            self._stream._read_buffer.clear()
            self._stream._read_buffer_size = 0
            return self._rbuffer.read(sz)
        else:
            child_gr = greenlet.getcurrent()
            main = child_gr.parent
            self._stream.read_bytes(sz,lambda data:child_gr.switch(data))
            return main.switch()

class TIOStreamTransportPool(object):
    def __init__(self, pool):
        self._pool = pool

    def get_transport(self):
        return TGrIOStreamTransport(self._pool.get_stream())

    def release_transport(self, transport):
        self._pool.release_stream(transport._stream)