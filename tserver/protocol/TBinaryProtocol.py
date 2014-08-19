# -*- coding: utf-8 -*-
#14-6-12
# create by: snower

import struct
from thrift.protocol import TProtocol
from thrift.protocol import TBinaryProtocol

class TBinaryProtocol(TBinaryProtocol.TBinaryProtocol):
    def readMessageBegin(self,callback):
        def read_size(sz):
            if sz < 0:
                version = sz & TBinaryProtocol.VERSION_MASK
                if version != TBinaryProtocol.VERSION_1:
                    raise TProtocol.TProtocolException(
                        type=TProtocol.TProtocolException.BAD_VERSION,
                        message='Bad version in readMessageBegin: %d' % (sz))
                type = sz & TBinaryProtocol.TYPE_MASK

                self.readString(lambda name: self.readI32(lambda seqid: callback((name,type,seqid))))
            else:
                if self.strictRead:
                    raise TProtocol.TProtocolException(type=TProtocol.TProtocolException.BAD_VERSION,
                                             message='No protocol version header')
                self.trans.read(sz+5,lambda buff:callback((buff[:sz],self.unpackByte(buff[sz]),self.unpackI32(buff[sz+1:]))))
        self.readI32(read_size)

    def readMessageEnd(self,callback):
        callback()

    def readStructBegin(self,callback):
        callback()

    def readStructEnd(self,callback):
        callback()

    def readFieldBegin(self,callback):
        self.readByte(lambda type:callback((None, type, 0)) if type == TProtocol.TType.STOP else self.readI16(lambda id:callback((None, type, id))))

    def readFieldEnd(self,callback):
        callback()

    def readMapBegin(self,callback):
        self.trans.read(6,lambda buff:callback((self.unpackByte(buff[0]), self.unpackByte(buff[1]), self.unpackI32(buff[2:]))))

    def readMapEnd(self,callback):
        callback()

    def readListBegin(self,callback):
        self.trans.read(5,lambda buff:callback((self.unpackByte(buff[0]), self.unpackI32(buff[1:]))))

    def readListEnd(self,callback):
        callback()

    def readSetBegin(self,callback):
        self.trans.read(5,lambda buff:callback((self.unpackByte(buff[0]), self.unpackI32(buff[1:]))))

    def readSetEnd(self,callback):
        callback()

    def readBool(self,callback):
        self.readByte(lambda byte:callback(byte == 0))

    def unpackByte(self,buff):
        return struct.unpack('!b', buff)[0]

    def readByte(self,callback):
        self.trans.read(1,lambda buff:callback(self.unpackByte(buff)))

    def unpackI16(self,buff):
        return struct.unpack('!h', buff)[0]

    def readI16(self,callback):
        self.trans.read(2,lambda buff:callback(self.unpackI16(buff)))

    def unpackI32(self,buff):
        return struct.unpack('!i', buff)[0]

    def readI32(self,callback):
        self.trans.read(4,lambda buff:callback(self.unpackI32(buff)))

    def unpackI64(self,buff):
        return struct.unpack('!q', buff)[0]

    def readI64(self,callback):
        self.trans.read(8,lambda buff:callback(self.unpackI64(buff)))

    def unpackDouble(self,buff):
        return struct.unpack('!d', buff)[0]

    def readDouble(self,callback):
        self.trans.read(8,lambda buff:callback(self.unpackDouble(buff)))

    def readString(self,callback):
        self.readI32(lambda sz: self.trans.read(sz,callback))

    def skip(self, ttype, callback):
        if ttype == TProtocol.TType.STOP:
            return
        elif ttype == TProtocol.TType.BOOL:
            self.readBool(lambda v:callback())
        elif ttype == TProtocol.TType.BYTE:
            self.readByte(lambda v:callback())
        elif ttype == TProtocol.TType.I16:
            self.readI16(lambda v:callback())
        elif ttype == TProtocol.TType.I32:
            self.readI32(lambda v:callback())
        elif ttype == TProtocol.TType.I64:
            self.readI64(lambda v:callback())
        elif ttype == TProtocol.TType.DOUBLE:
            self.readDouble(lambda v:callback())
        elif ttype == TProtocol.TType.STRING:
            self.readString(lambda v:callback())
        elif ttype == TProtocol.TType.STRUCT:
            def read_field(args):
                name, ttype, id=args
                if ttype == TProtocol.TType.STOP:
                    self.readStructEnd(lambda :callback())
                    return
                self.skip(ttype,lambda :self.readFieldEnd(lambda :self.readFieldBegin(read_field)))

            self.readStructBegin(lambda :self.readFieldBegin(read_field))

        elif ttype == TProtocol.TType.MAP:
            (ktype, vtype, size) = self.readMapBegin()
            for i in xrange(size):
                self.skip(ktype)
                self.skip(vtype)
            self.readMapEnd()
        elif ttype == TProtocol.TType.SET:
            (etype, size) = self.readSetBegin()
            for i in xrange(size):
                self.skip(etype)
            self.readSetEnd()
        elif ttype == TProtocol.TType.LIST:
            (etype, size) = self.readListBegin()
            for i in xrange(size):
                self.skip(etype)
            self.readListEnd()

class TBinaryProtocolFactory:
    def __init__(self, strictRead=False, strictWrite=True):
        self.strictRead = strictRead
        self.strictWrite = strictWrite

    def getProtocol(self, trans):
        prot = TBinaryProtocol(trans, self.strictRead, self.strictWrite)
        return prot