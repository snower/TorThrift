# -*- coding: utf-8 -*-
# 15/9/19
# create by: snower

import greenlet
from tornado.gen import coroutine as tornado_coroutine
from tornado.gen import *

def coroutine(fun):
    fun = tornado_coroutine(fun)
    def _(*args, **kwargs):
        future = fun(*args, **kwargs)
        if not is_future(future):
            return future

        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Execut must be running in child greenlet"

        def finish(future):
            if future._exc_info is not None:
                child_gr.throw(future.exception())
            return child_gr.switch(future.result())
        IOLoop.current().add_future(future, finish)
        return main.switch()
    return _