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
        future = func(*args, **kwargs)

        child_gr = greenlet.getcurrent()
        main = child_gr.parent

        def final_callback(future):
            if main is None:
                if future.result() is not None:
                    raise ReturnValueIgnoredError(
                        "@gen.engine functions cannot return values: %r" %
                        (future.result(),))
            else:
                if future._exc_info is not None:
                    return child_gr.throw(future.exception())
                elif future.result() is not None:
                    return child_gr.throw(ReturnValueIgnoredError("@gen.engine functions cannot return values: %r" %(future.result(),)))
                return child_gr.switch(None)
        future.add_done_callback(stack_context.wrap(final_callback))
        return main and main.switch()
    return wrapper

def coroutine(fun):
    fun = tornado_coroutine(fun)

    def _(*args, **kwargs):
        future = fun(*args, **kwargs)
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        if main is None:
            return future

        def finish(future):
            if future._exc_info is not None:
                return child_gr.throw(future.exception())
            return child_gr.switch(future.result())
        IOLoop.current().add_future(future, finish)
        return main and main.switch()
    return _