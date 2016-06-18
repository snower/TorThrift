# -*- coding: utf-8 -*-
#16-6-18
# create by: snower

import greenlet
from tornado.ioloop import IOLoop
from tornado.concurrent import is_future

class HandlerWrapper(object):
    def __init__(self, processor, handler):
        self._processor = processor
        self._handler = handler

    def __getattr__(self, name):
        if name not in self._processor._processMap:
            return getattr(self._handler, name)

        func = getattr(self._handler, name)
        ioloop = IOLoop.current()

        def _(*args, **kwargs):
            child_gr = greenlet.getcurrent()
            main = child_gr.parent
            if main is None:
                return func(*args, **kwargs)

            def finish(future):
                if future._exc_info is not None:
                    return child_gr.throw(future.exception())
                return child_gr.switch(future.result())

            def run():
                result = func(*args, **kwargs)
                if not is_future(result):
                    return child_gr.switch(result)
                return ioloop.add_future(result, finish)

            ioloop.add_callback(run)
            return main.switch()

        setattr(self, name, _)
        return _