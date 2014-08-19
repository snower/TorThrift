# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import sys
from tornado.concurrent import TracebackFuture
from tornado.iostream import StreamClosedError
from thrift.transport import TTransport

class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        return TIOStreamTransport(stream)


class TIOStreamTransport(TTransport.TTransportBase):
    def __init__(self, stream):
        self._stream = stream

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
        if sz<=self._stream._read_buffer_size:
            print sz, callback, "cache"
            callback(self._stream._consume(sz))
        else:
            print sz, callback, "nocache"
            self._stream.read_bytes(sz,callback)

    def write(self, data):
        self._stream.write(data)

    def flush(self):
        pass

class TIOStreamTransportPool(object):
    def __init__(self, pool):
        self._pool = pool

    def get_transport(self):
        future = TracebackFuture()
        try:
            stream_future = self._pool.get_stream()
            def finish(stream):
                try:
                    stream = stream_future.result()
                    future.set_result(TIOStreamTransport(stream))
                except Exception:
                    future.set_exc_info(stream_future.exc_info())
            stream_future.add_done_callback(finish)
        except Exception:
            future.set_exc_info(sys.exc_info())
        return future

    def release_transport(self, transport):
        self._pool.release_stream(transport._stream)