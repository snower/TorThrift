# -*- coding: utf-8 -*-
#16-6-18
# create by: snower

import sys
import greenlet
import functools
from tornado.ioloop import IOLoop
from tornado.concurrent import is_future, Future

class HandlerWrapper(object):
    def __init__(self, server, processor, handler):
        self._server = server
        self._processor = processor
        self._handler = handler

    def __getattr__(self, name):
        if name not in self._processor._processMap:
            return getattr(self._handler, name)

        func = getattr(self._handler, name)
        ioloop = IOLoop.current()

        def run(child_gr, *args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if not is_future(result):
                    return child_gr.switch(result)
            except:
                exc_info = sys.exc_info()
                result = Future()
                result.set_exc_info(exc_info)
            return ioloop.add_future(result, child_gr.switch)

        @functools.wraps(func)
        def _(*args, **kwargs):
            self._server.handing_count += 1
            try:
                child_gr = greenlet.getcurrent()
                main = child_gr.parent
                if main is None:
                    return func(*args, **kwargs)

                ioloop.add_callback(run, child_gr, *args, **kwargs)
                result = main.switch()
                if is_future(result):
                    result = result.result()
                return result
            finally:
                self._server.handing_count -= 1

        setattr(self, name, _)
        return _