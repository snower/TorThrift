# -*- coding: utf-8 -*-
#14-6-24
# create by: snower

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
sys.path.append(os.path.abspath(os.path.abspath(os.path.dirname(__file__))+os.sep+"gen-py"))

from thrift.protocol.TBinaryProtocol import TBinaryProtocolAcceleratedFactory
from torthrift.transport import TIOStreamTransportFactory
from torthrift.server import TTornadoServer
from example.Example import Processor
from tornado.ioloop import IOLoop
from torthrift import gen

class Handler(object):
    @gen.coroutine
    def add(self,a,b):
        raise gen.Return(a+b)

if __name__=="__main__":
    handler = Handler()
    processor = Processor(handler)
    tfactory = TIOStreamTransportFactory()
    protocol =TBinaryProtocolAcceleratedFactory()

    server = TTornadoServer(processor, tfactory, protocol)
    server.bind(20000)
    server.start(0)
    IOLoop.instance().start()