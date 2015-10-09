# -*- coding: utf-8 -*-
#14-6-11
# create by: snower

from setuptools import setup

setup(
    name='torthrift',
    version='0.0.5',
    packages=['torthrift','torthrift.server','torthrift.transport'],
    package_data={
        '': ['README.md'],
    },
    install_requires=['thrift>=0.9.1','tornado>=3.2.1', 'greenlet>=0.4.2',],
    author='snower',
    author_email='sujian199@gmail.com',
    url='http://github.com/snower/TorThrift',
    license='MIT',
    description='Thrift Tornado server',
    long_description='Thrift Tornado server'
)
