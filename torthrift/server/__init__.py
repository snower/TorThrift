# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import logging
import greenlet
from tornado import tcpserver

class TTornadoServer(tcpserver.TCPServer):
    def __init__(self, processor, input_transport_factory, input_protocol_factory, output_transport_factory = None, output_protocol_factory = None):
        super(TTornadoServer,self).__init__()
        self.processor = processor
        self.input_transport_factory = input_transport_factory
        self.output_transport_factory = output_transport_factory or input_transport_factory
        self.input_protocol_factory = input_protocol_factory
        self.output_protocol_factory = output_protocol_factory or input_protocol_factory

    def process(self, itrans, otrans):
        iprot = self.input_protocol_factory.getProtocol(itrans)
        oprot = self.output_protocol_factory.getProtocol(otrans)
        while itrans.closed and otrans.closed:
            try:
                self.processor.process(iprot, oprot)
            except Exception as e:
                logging.error("processor error:%s", e)
        itrans.close()
        otrans.close()

    def handle_stream(self, stream, address):
        itrans = self.input_transport_factory.getTransport(stream)
        otrans = self.output_transport_factory.getTransport(stream)
        child_gr = greenlet.greenlet(self.process)
        child_gr.switch(itrans, otrans)