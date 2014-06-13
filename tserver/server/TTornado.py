# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import logging
from thrift.server import TServer
from tornado.ioloop import IOLoop

class TTornadoServer(TServer.TServer):
    def start(self,num_processes=1):
        self.serverTransport.start(self,num_processes)
        self.ioloop=IOLoop.current()

    def stop(self):
        self.serverTransport.stop()

    def accept(self,stream):
        itrans = self.inputTransportFactory.getTransport(stream)
        otrans = self.outputTransportFactory.getTransport(stream)
        iprot = self.inputProtocolFactory.getProtocol(itrans)
        oprot = self.outputProtocolFactory.getProtocol(otrans)

        def next():
            self.ioloop.add_callback(process)

        def process():
            if itrans.isOpen():
                try:
                    self.processor.process(iprot, oprot,callback=next)
                except:
                    itrans.close()
                    otrans.close()
            else:
                itrans.close()
                otrans.close()
        next()