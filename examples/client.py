# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
sys.path.append(os.path.abspath(os.path.abspath(os.path.dirname(__file__))+os.sep+"gen-py"))

import time
from example.Example import Client
from thrift import Thrift
from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol.TBinaryProtocol import TBinaryProtocolAccelerated

try:
    transport = TSocket('127.0.0.1', 20000)
    transport = TBufferedTransport(transport)
    protocol = TBinaryProtocolAccelerated(transport)
    client = Client(protocol)

    transport.open()

    start = time.time()
    for i in range(10000):
        result = client.add(0,i)
    print time.time()-start

except Thrift.TException, ex:
    print "%s" % (ex.message)