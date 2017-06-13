# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
import greenlet
from collections import deque
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from thrift.transport import TTransport


if sys.version_info[0] >= 3:
    import io
    StringIO = io.BytesIO

    def to_tytes(data):
        if isinstance(data, str):
            return bytes(data, 'utf-8')
        return data
else:
    import cStringIO
    StringIO = cStringIO.StringIO


    def to_tytes(data):
        if isinstance(data, unicode):
            return data.encode("utf-8")
        return data


class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        return TIOStreamTransport(stream)


class TIOStreamTransport(TTransport.TTransportBase, TTransport.CReadableTransport):
    DEFAULT_BUFFER = 4096

    def __init__(self, stream):
        self._stream = stream
        self._wbuffer = deque()
        self._wbuffer_len = 0
        self._rbuffer = StringIO(b'')
        self._loop = IOLoop.current()

    def open(self):
        try:
            future = self._stream.open()
        except:
            exc_info = sys.exc_info()
            future = Future()
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
        except Exception as e:
            raise TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e))

    def read(self, sz):
        data = self._rbuffer.read(sz)
        if len(data) >= sz:
            return data
        partialread = data
        partialread_len = len(data)

        if sz - partialread_len <= self._stream._read_buffer_size:
            data, data_len = self._stream._read_buffer, self._stream._read_buffer_size
            self._stream._read_buffer = bytearray()
            self._stream._read_buffer_size = 0

            if partialread_len + data_len == sz:
                return bytes(partialread + data)

            self._rbuffer = StringIO(data)
            return partialread + self._rbuffer.read(sz - partialread_len)

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def read_callback(future):
            try:
                data = future.result()
            except Exception as e:
                return child_gr.throw(TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e)))

            if partialread_len + len(data) == sz:
                return child_gr.switch(bytes(partialread + data))

            self._rbuffer = StringIO(data)
            return child_gr.switch(partialread + self._rbuffer.read(sz - partialread_len))

        future = self._stream.read(sz - partialread_len)
        self._loop.add_future(future, read_callback)
        return main.switch()

    def write(self, data):
        data = to_tytes(data)
        self._wbuffer.append(data)
        self._wbuffer_len += len(data)
        if self._wbuffer_len >= self.DEFAULT_BUFFER:
            data = b"".join(self._wbuffer)
            self._wbuffer.clear()
            self._wbuffer_len = 0

            try:
                self._stream.write(data)
            except Exception as e:
                raise TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e))

    def flush(self):
        if self._wbuffer_len:
            data = b"".join(self._wbuffer)
            self._wbuffer.clear()
            self._wbuffer_len = 0
        else:
            data = b''

        try:
            future = self._stream.write(data)
        except Exception as e:
            raise TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e))

        if future.done():
            return

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def write_callback(future):
            try:
                result = future.result()
            except Exception as e:
                return child_gr.throw(TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e)))
            return child_gr.switch(result)

        self._loop.add_future(future, write_callback)
        return main.switch()

    @property
    def cstringio_buf(self):
        return self._rbuffer

    def cstringio_refill(self, partialread, reqlen):
        partialread_len = len(partialread)

        if reqlen - partialread_len <= self._stream._read_buffer_size:
            self._rbuffer = StringIO(partialread + self._stream._read_buffer)
            self._stream._read_buffer = bytearray()
            self._stream._read_buffer_size = 0
            return self._rbuffer

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def read_callback(future):
            try:
                data = future.result()
            except Exception as e:
                return child_gr.throw(TTransport.TTransportException(TTransport.TTransportException.END_OF_FILE, str(e)))

            self._rbuffer = StringIO(partialread + data)
            return child_gr.switch(self._rbuffer)

        future = self._stream.read(reqlen - partialread_len)
        self._loop.add_future(future, read_callback)
        return main.switch()