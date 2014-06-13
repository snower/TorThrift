# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

import logging
import socket
from tornado import tcpserver
from thrift.transport import TTransport
from tornado.iostream import IOStream
from tornado import gen

class TServerStream(tcpserver.TCPServer,TTransport.TServerTransportBase):
    """Base class for Thrift server transports."""
    def __init__(self,host,port):
        tcpserver.TCPServer.__init__(self)
        self.__host=host
        self.__port=port
        self.__server=None

    def start(self, server, num_processes=1):
        self.__server=server
        self.bind(self.__port,self.__host)
        tcpserver.TCPServer.start(self,num_processes)

    def handle_stream(self, stream, address):
        self.__server.accept(stream)

    def close(self):
        self.stop()