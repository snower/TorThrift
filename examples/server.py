# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
sys.path.append(os.path.abspath(os.path.abspath(os.path.dirname(__file__))+os.sep+"gen-py"))

from thrift.transport.TSocket import TServerSocket
from thrift.protocol.TBinaryProtocol import TBinaryProtocolAcceleratedFactory
from thrift.transport.TTransport import TBufferedTransportFactory
from thrift.server.TProcessPoolServer import TProcessPoolServer
from example.Example import Processor

class Handler(object):
    def add(self,a,b):
        return a+b

if __name__=="__main__":
    handler = Handler()
    processor = Processor(handler)
    transport = TServerSocket(port=20000)
    tfactory = TBufferedTransportFactory()
    protocol =TBinaryProtocolAcceleratedFactory()

    server = TProcessPoolServer(processor, transport, tfactory, protocol)
    server.setNumWorkers(10)
    server.serve()
