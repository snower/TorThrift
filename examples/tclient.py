# -*- coding: utf-8 -*-
#14-6-24
# create by: snower

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
sys.path.append(os.path.abspath(os.path.abspath(os.path.dirname(__file__))+os.sep+"gen-py"))

import time
from tornado.ioloop import IOLoop
from tornado import gen
from example.Example import Client
from thrift import Thrift
from torthrift.transport import TStreamPool
from torthrift.transport import TIOStreamTransportPool
from torthrift.protocol import TBinaryProtocolPool
from torthrift.client import PoolClient

@gen.coroutine
def test():
    try:
        transport = TStreamPool('127.0.0.1', 20000, max_stream=10)
        transport = TIOStreamTransportPool(transport)
        protocol = TBinaryProtocolPool(transport)
        client = PoolClient(Client, protocol)

        start = time.time()
        futures = []
        for i in range(10000):
            futures.append(client.add(0,i))
        yield futures
        print time.time()-start

    except Thrift.TException, ex:
        print "%s" % (ex.message)
    ioloop.stop()

def start():
    test()

ioloop = IOLoop.instance()
ioloop.add_callback(start)
ioloop.start()