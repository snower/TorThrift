TorThrift
========

.. image:: https://travis-ci.org/snower/TorMySQL.svg
    :target: https://travis-ci.org/snower/TorMySQL

Tornado asynchronous thrift server and client

About
=====

torthrift - presents a Tornado Future-based API and greenlet for
non-blocking thrift server and client.

Installation
============

::

    pip install TorThrift

Examples
========

server.py

::

    from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
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
        protocol =TBinaryProtocolFactory()
    
        server = TTornadoServer(processor, tfactory, protocol)
        server.bind(20000)
        server.start(0)
        IOLoop.instance().start()
        
client.py
    
::

    from tornado.ioloop import IOLoop
    from tornado import gen
    from example.Example import Client
    from thrift import Thrift
    from torthrift.pool import TStreamPool
    from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
    from torthrift.client import PoolClient
    
    @gen.coroutine
    def test():
        try:
            transport = TStreamPool('127.0.0.1', 20000, max_stream=10)
            client = PoolClient(Client, transport, TBinaryProtocolFactory())
    
            res = yield client.add(0,i)
            print res
            yield client.close()
        except Thrift.TException as ex:
            print("%s" % (ex.message))
        ioloop.stop()
    
    ioloop = IOLoop.instance()
    ioloop.add_callback(test)
    ioloop.start()