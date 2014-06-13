# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

from thrift.transport import TTransport

class TIOStreamTransportFactory:
    """Factory transport that builds buffered transports"""

    def getTransport(self, stream):
        buffered = TIOStreamTransport(stream)
        return buffered


class TIOStreamTransport(TTransport.TTransportBase):
    def __init__(self, stream):
        self.__stream = stream
        self.__wbuf=TTransport.StringIO()

    def isOpen(self):
        return not self.__stream.closed()

    def close(self):
        return self.__stream.close()

    def read(self, sz, callback):
        self.__stream.read_bytes(sz,callback)

    def write(self, buf):
        self.__wbuf.write(buf)

    def flush(self):
        out = self.__wbuf.getvalue()
        self.__wbuf = TTransport.StringIO()
        self.__stream.write(out)