# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import logging
import traceback
from tornado import tcpserver
from thrift.server import TServer
from tornado.ioloop import IOLoop

class TTornadoServer(tcpserver.TCPServer,TServer.TServer):
    def __init__(self,*args,**kwargs):
        tcpserver.TCPServer.__init__(self)
        TServer.__init__(self,*args,**kwargs)

    def handle_stream(self, stream, address):
        itrans = self.inputTransportFactory.getTransport(stream)
        otrans = self.outputTransportFactory.getTransport(stream)
        iprot = self.inputProtocolFactory.getProtocol(itrans)
        oprot = self.outputProtocolFactory.getProtocol(otrans)

        def next():
            self.io_loop.add_callback(process)

        def process():
            if itrans.isOpen():
                try:
                    self.processor.process(iprot, oprot,callback=next)
                    return
                except Exception:
                    logging.error("processor error:%s",traceback.format_exc())
            itrans.close()
            otrans.close()
        next()