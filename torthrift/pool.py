# -*- coding: utf-8 -*-
# 14-8-19
# create by: snower

import time
import logging
from collections import deque
from tornado.ioloop import IOLoop
from tornado.gen import Future
from tornado.iostream import StreamClosedError
from thrift.transport.TTransport import TTransportException
from .transport.stream import TStream as BaseTStream

class TStreamPoolClosedError(Exception):
    pass


class TStream(BaseTStream):
    def __init__(self, *args, **kwargs):
        super(TStream, self).__init__(*args, **kwargs)

        self.used_time = time.time()
        self.idle_time = time.time()


class TStreamPool(object):
    def __init__(self, *args, **kwargs):
        self._max_stream = kwargs.pop("max_stream") if "max_stream" in kwargs else 1
        self._idle_seconds = kwargs.pop("idle_seconds") if "idle_seconds" in kwargs else 0
        self._args = args
        self._kwargs = kwargs
        self._streams = deque()
        self._used_streams = {}
        self._stream_count = 0
        self._wait_streams = deque()
        self._check_idle = False
        self._closed = False
        self._close_callback = None
        self._close_future = None

    def set_close_callback(self, callback):
        self._close_callback = callback

    def stream_close_callback(self, stream):
        try:
            del self._used_streams[id(stream)]
            self._stream_count -= 1
        except KeyError:
            try:
                self._streams.remove(stream)
                self._stream_count -= 1
            except ValueError:
                logging.error("close unknown stream %s", stream)

        if self._closed and not self._streams and not self._used_streams:
            if self._close_callback:
                self._close_callback()
            if self._close_future:
                self._close_future.set_result(True)

    def init_stream(self, future):
        stream = TStream(*self._args, **self._kwargs)
        stream.set_close_callback(lambda : self.stream_close_callback(stream))
        open_future = stream.open()
        self._used_streams[id(stream)] = stream
        self._stream_count += 1

        def finish(open_future):
            try:
                open_future.result()
            except StreamClosedError as e:
                future.set_exception(TTransportException(TTransportException.NOT_OPEN, str(e)))
            except:
                future.set_exc_info(open_future.exc_info())
            else:
                future.set_result(stream)
        IOLoop.current().add_future(open_future, finish)

        if self._idle_seconds > 0 and not self._check_idle:
            IOLoop.current().add_timeout(time.time() + self._idle_seconds, self.check_idle)
            self._check_idle = True

    def get_stream(self):
        if self._closed:
            raise TStreamPoolClosedError()

        future = Future()
        while self._streams:
            stream = self._streams.pop()
            self._used_streams[id(stream)] = stream
            stream.used_time = time.time()
            if not stream.closed():
                future.set_result(stream)
                return future

        if self._stream_count < self._max_stream:
            self.init_stream(future)
        else:
            self._wait_streams.append(future)
        return future

    def release_stream(self, stream):
        release_future = Future()
        release_future.set_result(None)

        if stream.closed():
            return release_future

        if not self._wait_streams:
            if self._closed:
                stream.close()
            else:
                try:
                    del self._used_streams[id(stream)]
                    stream.idle_time = time.time()
                    self._streams.append(stream)
                except KeyError:
                    logging.error("release unknown stream %s", stream)
        else:
            future = self._wait_streams.popleft()
            stream.used_time = time.time()
            future.set_result(stream)

            while self._wait_streams and self._streams:
                stream = self._streams.pop()
                self._used_streams[id(stream)] = stream
                stream.used_time = time.time()
                if not stream.closed():
                    future = self._wait_streams.popleft()
                    future.set_result(stream)

        return release_future

    def check_idle(self):
        for stream in list(self._streams):
            if time.time() - stream.idle_time > self._idle_seconds:
                self._streams.remove(stream)
                self._used_streams[id(stream)] = stream
                stream.close()
        if self._idle_seconds > 0 and self._streams and self._used_streams:
            IOLoop.current().add_timeout(time.time() + self._idle_seconds, self.check_idle)
        else:
            self._check_idle = False

    def close(self):
        self._close_future = Future()
        self._closed = True

        while self._wait_streams:
            future = self._wait_streams.popleft()
            future.set_exception(TStreamPoolClosedError())

        while self._streams:
            stream = self._streams.popleft()
            self._used_streams[id(stream)] = stream
            stream.close()
        return self._close_future