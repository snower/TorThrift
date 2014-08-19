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
from thrift.protocol.TBinaryProtocol import TBinaryProtocol

try:
    transport = TSocket('127.0.0.1', 10000)
    transport = TBufferedTransport(transport)
    protocol = TBinaryProtocol(transport)
    client = Client(protocol)

    transport.open()

    start = time.time()
    for i in range(100000):
        t = time.time()
        result = client.add(0,i)
        print result,time.time()-t
    print time.time()-start

except Thrift.TException, ex:
    print "%s" % (ex.message)