# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import sys
import greenlet
from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from .transport.transport import TIOStreamTransportFactory


def async_call_method(fun, *args, **kwargs):
    future = Future()
    def finish():
        try:
            result = fun(*args, **kwargs)
            if future._callbacks:
                IOLoop.current().add_callback(future.set_result, result)
            else:
                future.set_result(result)
        except:
            if future._callbacks:
                IOLoop.current().add_callback(future.set_exc_info, sys.exc_info())
            else:
                future.set_exc_info(sys.exc_info())
    child_gr = greenlet.greenlet(finish)
    child_gr.switch()
    return future


class PoolClient(object):
    def __init__(self, client_class, itrans_pool, pfactory, tfactory = TIOStreamTransportFactory(), otrans_pool=None):
        self._client_class = client_class
        self._itrans_pool = itrans_pool
        self._otrans_pool = otrans_pool
        self._tfactory = tfactory
        self._pfactory = pfactory

    def __getattr__(self, name):
        @gen.coroutine
        def _(*args, **kwargs):
            istream = yield self._itrans_pool.get_stream()
            ostream = (yield self._otrans_pool.get_stream()) if self._otrans_pool else None
            iprot = self._pfactory.getProtocol(self._tfactory.getTransport(istream))
            oprot = self._pfactory.getProtocol(self._tfactory.getTransport(ostream)) if ostream else None
            client = self._client_class(iprot, oprot)
            try:
                result = yield async_call_method(getattr(client, name), *args, **kwargs)
            finally:
                self._itrans_pool.release_stream(istream)
                if ostream:
                    self._otrans_pool.release_stream(ostream)
            raise gen.Return(result)
        setattr(self, name, _)
        return _
