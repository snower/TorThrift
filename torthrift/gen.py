# -*- coding: utf-8 -*-
# 15/9/19
# create by: snower

import greenlet
from tornado.gen import coroutine as tornado_coroutine, _make_coroutine_wrapper
from tornado.gen import *

def engine(func):
    func = _make_coroutine_wrapper(func, replace_callback=False)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent

        if main is None:
            future = func(*args, **kwargs)
            def final_callback(future):
                if future.result() is not None:
                    raise ReturnValueIgnoredError(
                        "@gen.engine functions cannot return values: %r" %
                        (future.result(),))
            future.add_done_callback(stack_context.wrap(final_callback))
            return

        def run():
            future = func(*args, **kwargs)
            def final_callback(future):
                if future._exc_info is not None:
                    return child_gr.throw(future.exception())
                elif future.result() is not None:
                    return child_gr.throw(ReturnValueIgnoredError("@gen.engine functions cannot return values: %r" %(future.result(),)))
                return child_gr.switch(None)
            future.add_done_callback(stack_context.wrap(final_callback))
        IOLoop.current().add_callback(run)
        return main.switch()
    return wrapper

def coroutine(func, replace_callback=True):
    func = tornado_coroutine(func, replace_callback)

    @functools.wraps(func)
    def _(*args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        if main is None:
            return func(*args, **kwargs)

        ioloop = IOLoop.current()
        def run():
            future = func(*args, **kwargs)
            def finish(future):
                if future._exc_info is not None:
                    return child_gr.throw(future.exception())
                return child_gr.switch(future.result())
            ioloop.add_future(future, finish)
        ioloop.add_callback(run)
        return main.switch()
    return _