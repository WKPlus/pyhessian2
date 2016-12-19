try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

VERSION = '1.1.1'

LONG_DESCRIPTION = '''
pyhessian2 is implemented for serialize and deserialize data in hessian2 protocol.

Usage
-----

    >>> # encoding
    >>> from pyhessian2 import HessianObject, Encoder
    >>> attrs = {
            "name": "xx",
            "age": 20,
        }
    >>> obj = HessianObject("com.xx.person", attrs)
    >>> data = Encoder().encode(obj)
    >>> print "%r" % data


    >>> # decoding
    >>> from pyhessian2 import Decoder
    >>> data = ...  # a hessian bytes data
    >>> obj = Decoder().decoder(data)  # get a Hessianobject instance
    >>> print obj  # print json serialized data


'''

setup(
    name='pyhessian2',
    description='an implementation for hessian2',
    long_description=LONG_DESCRIPTION,
    author='WKPlus',
    url='https://github.com/WKPlus/pyhessian2.git',
    license='MIT',
    author_email='qifa.zhao@gmail.com',
    version=VERSION,
    packages = ['pyhessian2'],
    install_requires=[],
    test_requires=['nose'],
    zip_safe=False,
)
