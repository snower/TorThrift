# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

from tornado.iostream import StreamClosedError
from thrift.transport import TTransport

class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        buffered = TIOStreamTransport(stream)
        return buffered


class TIOStreamTransport(TTransport.TTransportBase):
    MAX_BUFFER_SIZE=16*1024

    def __init__(self, stream):
        self.__stream = stream
        self.__wbuf=TTransport.StringIO()

    def isOpen(self):
        return not self.__stream.closed()

    def close(self):
        return self.__stream.close()

    def read(self, sz, callback):
        if sz<=self.__stream._read_buffer_size:
            callback(self.__stream._consume(sz))
        else:
            self.__stream.read_bytes(sz,callback)

    def write(self, buf):
        self.__wbuf.write(buf)
        if self.__wbuf.tell()>self.MAX_BUFFER_SIZE:
            self.flush()

    def flush(self):
        out = self.__wbuf.getvalue()
        self.__wbuf = TTransport.StringIO()
        try:
            self.__stream.write(out)
        except StreamClosedError:
            pass