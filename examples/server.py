# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
sys.path.append(os.path.abspath(os.path.abspath(os.path.dirname(__file__))+os.sep+"gen-py"))

from thrift.transport.TSocket import TServerSocket
from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
from thrift.transport.TTransport import TBufferedTransportFactory
from thrift.server.TServer import TSimpleServer
from example.Example import Processor

class Handler(object):
    def add(self,a,b):
        print a+b
        return a+b

if __name__=="__main__":
    handler = Handler()
    processor = Processor(handler)
    transport = TServerSocket(port=10000)
    tfactory = TBufferedTransportFactory()
    protocol =TBinaryProtocolFactory()

    server = TSimpleServer(processor, transport, tfactory, protocol)
    server.serve()
