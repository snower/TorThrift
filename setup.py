# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

from setuptools import setup

setup(
    name='torthrift',
    version='0.0.1',
    packages=['tserver','tserver.protocol','tserver.server','tserver.transport'],
    package_data={
        '': ['README.md'],
    },
    install_requires=['thrift>=0.9.1','tornado>=3.2.1'],
    author='snower',
    author_email='sujian199@gmail.com',
    url='http://github.com/snower/tserver',
    license='MIT',
    description='Thrift高性能的Tornado server',
    long_description='Thrift高性能的Tornado server'
)
