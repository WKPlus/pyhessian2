#-*- coding:utf8 -*-

'''
Hessian2.0 encoder implementation in python.

According to http://hessian.caucho.com/doc/hessian-serialization.html.

Hessian Bytecode map:
    x00 - x1f    # utf-8 string length 0-32
    x20 - x2f    # binary data length 0-16
    x30 - x33    # utf-8 string length 0-1023
    x34 - x37    # binary data length 0-1023
    x38 - x3f    # three-octet compact long (-x40000 to x3ffff)
    x40          # reserved (expansion/escape)
    x41          # 8-bit binary data non-final chunk ('A')
    x42          # 8-bit binary data final chunk ('B')
    x43          # object type definition ('C')
    x44          # 64-bit IEEE encoded double ('D')
    x45          # reserved
    x46          # boolean false ('F')
    x47          # reserved
    x48          # untyped map ('H')
    x49          # 32-bit signed integer ('I')
    x4a          # 64-bit UTC millisecond date
    x4b          # 32-bit UTC minute date
    x4c          # 64-bit signed long integer ('L')
    x4d          # map with type ('M')
    x4e          # null ('N')
    x4f          # object instance ('O')
    x50          # reserved
    x51          # reference to map/list/object - integer ('Q')
    x52          # utf-8 string non-final chunk ('R')
    x53          # utf-8 string final chunk ('S')
    x54          # boolean true ('T')
    x55          # variable-length list/vector ('U')
    x56          # fixed-length list/vector ('V')
    x57          # variable-length untyped list/vector ('W')
    x58          # fixed-length untyped list/vector ('X')
    x59          # long encoded as 32-bit int ('Y')
    x5a          # list/map terminator ('Z')
    x5b          # double 0.0
    x5c          # double 1.0
    x5d          # double represented as byte (-128.0 to 127.0)
    x5e          # double represented as short (-32768.0 to 32767.0)
    x5f          # double represented as float
    x60 - x6f    # object with direct type
    x70 - x77    # fixed list with direct length
    x78 - x7f    # fixed untyped list with direct length
    x80 - xbf    # one-octet compact int (-x10 to x3f, x90 is 0)
    xc0 - xcf    # two-octet compact int (-x800 to x7ff)
    xd0 - xd7    # three-octet compact int (-x40000 to x3ffff)
    xd8 - xef    # one-octet compact long (-x8 to xf, xe0 is 0)
    xf0 - xff    # two-octet compact long (-x800 to x7ff, xf8 is 0)
'''

from struct import pack
import datetime
import time
import types
from .proto import HessianObject, TypedMap, DoubleType


ONE_OCTET_INT_RANGE = (-0x10, 0x2f)
TWO_OCTET_INT_RANGE = (-0x800, 0x7ff)
THREE_OCTET_INT_RANGE = (-0x40000, 0x3ffff)

ONE_OCTET_LONG_RANGE = (-0x8, 0xf)
TWO_OCTET_LONG_RANGE = (-0x800, 0x7ff)
THREE_OCTET_LONG_RANGE = (-0x40000, 0x3ffff)
FOUR_OCTET_LONG_RANGE = (-0x80000000, 0x7fffffff)


class Encoder(object):
    def __init__(self):
        self._refs = []
        self._classes = []
        self.encoders = {
            types.NoneType: self.encode_null,
            types.BooleanType: self.encode_bool,
            datetime.datetime: self.encode_date,
            types.IntType: self.encode_int,
            types.LongType: self.encode_long,
            types.FloatType: self.encode_float,
            DoubleType: self.encode_double,
            types.ListType: self.encode_list,
            types.TupleType: self.encode_list,
            types.StringType: self.encode_string,
            types.UnicodeType: self.encode_string,
            types.DictType: self.encode_untyped_map,
            TypedMap: self.encode_typed_map,
            HessianObject: self.encode_object,
        }

    def encode(self, val):
        _type = type(val)
        if _type not in self.encoders:
            raise Exception("No encoder for type: %s" % _type)
        return self.encoders[_type](val)

    def encode_ref(self, val):
        # TODO: reference mark is 'Q' or 'R'? Use 'J' for 3.1.5
        '''
        x51          # reference to map/list/object - integer ('Q')
        '''
        _id = id(val)
        if _id in self._refs:
            ref_id = self._refs.index(_id)
            if ref_id <= 255:
                return '\x4a' + pack('>l', ref_id)[-1]
            elif ref_id <= 65535:
                return '\x4b' + pack('>l', ref_id)[-2:]
            else:
                raise Exception("Reference id too large: %d" % ref_id)
        self._refs.append(_id)

    def encode_null(self, val):
        return 'N'

    def encode_bool(self, val):
        if val:
            return 'T'
        else:
            return 'F'

    def encode_int(self, val):
        if ONE_OCTET_INT_RANGE[0] <= val <= ONE_OCTET_INT_RANGE[1]:
            # value = code - 0x90
            # b0 = b0 + 0x90
            return chr(val + 0x90)
        elif TWO_OCTET_INT_RANGE[0] <= val <= TWO_OCTET_INT_RANGE[1]:
            # value = ((code - 0xc8) << 8) + b0
            # b1 = b1 + 0xc8, b0 = b0
            return chr((val>>8) + 0xc8) + chr(val&0xff)
        elif THREE_OCTET_INT_RANGE[0] <= val <= THREE_OCTET_INT_RANGE[1]:
            # value = ((code - 0xd4) << 16) + (b1 << 8) + b0;
            # b2 = b2 + 0xd4, b1 = b1, b0 = b0
            return chr((val>>16) + 0xd4) + chr((val>>8)&0xff) + chr(val&0xff)
        elif (-2**31) <= val <= (2**31-1):
            return pack('>cl', 'I', val)
        else:
            # if a python int value is not in 32 bits range, encode it as long
            return pack('>cq', 'L', val)

    def encode_long(self, val):
        '''
        L b7 b6 b5 b4 b3 b2 b1 b0
        xd8 - xef    # one-octet compact long (-x8 to xf, xe0 is 0)
        xf0 - xff    # two-octet compact long (-x800 to x7ff, xf8 is 0)
        x38 - x3f    # three-octet compact long (-x40000 to x3ffff)
        x59          # long encoded as 32-bit int ('Y')
        x4c          # 64-bit signed long integer ('L')
        '''
        if ONE_OCTET_LONG_RANGE[0] <= val <= ONE_OCTET_LONG_RANGE[1]:
            # value = (code - 0xe0)
            # b0 = b0 + 0xe0
            return chr(val + 0xe0)
        elif TWO_OCTET_LONG_RANGE[0] <= val <= TWO_OCTET_LONG_RANGE[1]:
            # value = ((code - 0xf8) << 8) + b0
            # b1 = b1 + 0xf8, b0 = b0
            return chr((val>>8) + 0xf8) + chr(val&0xff)
        elif THREE_OCTET_LONG_RANGE[0] <= val <= THREE_OCTET_LONG_RANGE[1]:
            # value = ((code - 0x3c) << 16) + (b1 << 8) + b0
            # b2 = b2 + 0x3c, b1 = b1, b0 = b0
            return chr((val>>16) + 0x3c) + chr((val>>8)&0xff) + chr(val&0xff)
        elif FOUR_OCTET_LONG_RANGE[0] <= val <= FOUR_OCTET_LONG_RANGE[1]:
            # value = (b3 << 24) + (b2 << 16) + (b1 << 8) + b0
            return pack('>cl', '\x77', val)
        else:
            return pack('>cq', 'L', val)

    def encode_float(self, val):
        '''
        x44          # 64-bit IEEE encoded double ('D')
        x5b          # double 0.0
        x5c          # double 1.0
        x5d          # double represented as byte (-128.0 to 127.0)
        x5e          # double represented as short (-32768.0 to 32767.0)
        x5f          # double represented as float
        '''
        if val == 0.0:
            return '\x5b'
        elif val == 1.0:
            return '\x5c'

        if val.is_integer():
            _v = int(self, val)
            if -128 <= _v <= 127:
                return pack('>cb', '\x5d', _v)
            elif -32768 <= _v <= 32767:
                return pack('>ch', '\x5e', _v)

        try:
            return pack('>cf', '\x5f', val)
        except OverflowError:
            return pack('>cd', 'D', val)

    def encode_double(self, val):
        '''
        x44          # 64-bit IEEE encoded double ('D')
        x5b          # double 0.0
        x5c          # double 1.0
        x5d          # double represented as byte (-128.0 to 127.0)
        x5e          # double represented as short (-32768.0 to 32767.0)
        x5f          # double represented as float
        '''
        val = val.value
        if val == 0.0:
            return '\x5b'
        elif val == 1.0:
            return '\x5c'

        if val.is_integer():
            _v = int(self, val)
            if -128 <= _v <= 127:
                return pack('>cb', '\x5d', _v)
            elif -32768 <= _v <= 32767:
                return pack('>ch', '\x5e', _v)

        return pack('>cd', 'D', val)

    def encode_date(self, val):
        return pack('>cq', 'd', int(time.mktime(val.timetuple())) * 1000)

    def encode_binary(self, val):
        # TODO: non-final chunk mark is 'A' or 'b'? Use 'b'
        '''
        x20 - x2f    # binary data length 0-16
        x34 - x37    # binary data length 0-1023
        x41          # 8-bit binary data non-final chunk ('A')
        x42          # 8-bit binary data final chunk ('B')
        '''
        length = len(val)
        if length <= 15:
            return chr(length + 0x20) + val

        #if length <= 1023:
        #    # TODO: implement this by guess, find no spec to follow
        #    # length 0x3400 = 0, 0x37ff = 1023
        #    return chr((length>>8)+0x34) + chr(length&0xff) + val

        data = []
        index = 0
        chunk_max_size = 0xffff
        while length > chunk_max_size:
            data.append(pack('>cH','b',chunk_max_size))
            data.append(val[index:chunk_max_size])
            index += chunk_max_size
            length -= chunk_max_size

        # length must be in [1, chunk_max_size]
        data.append(pack('>cH', 'B', length))
        data.append(val[index:])
        return "".join(data)

    def encode_string(self, val):
        # TODO: non-final chunk mark is 'R' or 's'? Use 's'
        '''
        x00 - x1f    # utf-8 string length 0-32
        x30 - x33    # utf-8 string length 0-1023
        x52          # utf-8 string non-final chunk ('R')
        x53          # utf-8 string final chunk ('S')
        '''
        if isinstance(val, unicode):
            length = len(val)
            val = val.encode('utf8')
        elif isinstance(val, str):
            length = len(val.decode('utf8'))
        else:
            raise Exception(
                'encode string error, unknown type: %s' % type(val))
        if length <= 31:
            return chr(length) + val

        #if length <= 1023:
        #    # TODO: implement this by guess, find no spec to follow
        #    # length 0x3000 = 0, 0x33ff = 1023
        #    return chr((length>>8)+0x30) + chr(length&0xff) + val

        data = []
        index = 0
        chunk_max_size = 0xffff
        while length > chunk_max_size:
            data.append(pack('>cH','s',chunk_max_size))
            data.append(val[index:chunk_max_size])
            index += chunk_max_size
            length -= chunk_max_size

        # length must be in range [1, chunk_max_size]
        data.append(pack('>cH', 'S', length))
        data.append(val[index:])
        return "".join(data)

    def encode_list(self, val):
        ret = self.encode_ref(val)
        if ret:
            return ret
        length = len(val)
        data = []
        if length <= 0xff:
            data.append(pack('>2cB', 'V', 'n', length))
        else:
            data.append(pack('>2cl', 'V', 'l', length))

        for v in val:
            data.append(self.encode(v))
        data.append('z')
        return "".join(data)

    def encode_untyped_map(self, val):
        ret = self.encode_ref(val)
        if ret:
            return ret
        data = []
        data.append('H')
        for k, v in val.iteritems():
            data.append(self.encode(k))
            data.append(self.encode(v))
        data.append('z')
        return "".join(data)

    def encode_typed_map(self, val):
        ret = self.encode_ref(val)
        if ret:
            return ret
        _type, val= val._type, val.val
        data = []
        data.append('M')
        data.append(self.encode(_type))
        for k, v in val.iteritems():
            data.append(self.encode(k))
            data.append(self.encode(v))
        data.append('z')
        return "".join(data)

    def encode_object_class(self, val):
        data = []
        _class, attrs = val._class, val.attrs
        if _class in self._classes:
            return self._classes.index(_class), data

        data.append('O')
        data.append(self.encode_string(_class))
        length = len(attrs)
        data.append(self.encode_int(length))
        for k in attrs.iterkeys():
            data.append(self.encode_string(k))
        self._classes.append(_class)
        return len(self._classes) - 1, data

    def encode_object(self, val):
        ret = self.encode_ref(val)
        if ret:
            return ret
        ref_id, data = self.encode_object_class(val)
        data.append('o')
        attrs = val.attrs
        data.append(self.encode_int(ref_id))
        for v in attrs.itervalues():
            data.append(self.encode(v))
        return "".join(data)
