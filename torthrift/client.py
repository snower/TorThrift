# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

from tornado import gen

class PoolClient(object):
    def __init__(self, client_class, iprot_pool, oprot_pool=None):
        self._client_class = client_class
        self._iprot_pool = iprot_pool
        self._oprot_pool = oprot_pool

    def __getattr__(self, name):
        @gen.coroutine
        def _(*args, **kwargs):
            iprot = yield self._iprot_pool.get_protocol()
            oprot = (yield self._oprot_pool.get_protocol()) if self._oprot_pool else None
            client = self._client_class(iprot, oprot)
            try:
                result = yield getattr(client, name)(*args, **kwargs)
            finally:
                self._iprot_pool.release_protocol(iprot)
                if self._oprot_pool:
                    self._oprot_pool.release_protocol(oprot)
            raise gen.Return(result)
        return _
