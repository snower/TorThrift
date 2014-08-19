# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import sys
import greenlet
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop

class PoolClient(object):
    def __init__(self, client_class, iprot_pool, oprot_pool=None):
        self._client_class = client_class
        self._iprot_pool = iprot_pool
        self._oprot_pool = oprot_pool

    def __run(self, future, name, *args, **kwargs):
        try:
            iprot = self._iprot_pool.get_protocol()
            oprot = self._oprot_pool.get_protocol() if self._oprot_pool else None
            client = self._client_class(iprot, oprot)
            try:
                result = getattr(client, name)(*args, **kwargs)
            finally:
                self._iprot_pool.release_protocol(iprot)
                if self._oprot_pool:
                    self._oprot_pool.release_protocol(oprot)
            IOLoop.current().add_callback(lambda :future.set_result(result))
        except Exception:
            exc_info = sys.exc_info()
            IOLoop.current().add_callback(lambda :future.set_exc_info(exc_info))

    def __getattr__(self, name):
        def _(*args, **kwargs):
            future = TracebackFuture()
            child_gr = greenlet.greenlet(self.__run)
            child_gr.switch(future, name, *args, **kwargs)
            return future
        return _
