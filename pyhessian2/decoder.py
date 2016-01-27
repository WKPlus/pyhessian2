#-*- coding:utf8 -*-

'''
Hessian2.0 decoder implementation in python.

According to http://hessian.caucho.com/doc/hessian-serialization.html.
'''

from struct import unpack
from datetime import datetime
MKTIME = datetime.utcfromtimestamp
from .proto import HessianObjectFactory, TypedMap


ONE_INT_CODE_RANGE = ('\x80', '\xbf')
TWO_INT_CODE_RANGE = ('\xc0', '\xcf')
THREE_INT_CODE_RANGE = ('\xd0', '\xd7')

ONE_LONG_CODE_RANGE = ('\xd8', '\xef')
TWO_LONG_CODE_RANGE = ('\xf0', '\xff')
THREE_LONG_CODE_RANGE = ('\x38', '\x3f')
# ONE TWO THREE is short for ONE_OCTET TWO_OCTET THREE_OCTET

SHORT_STRING_CODE_RANGE = ('\x00', '\x1f')
SHORT_BINARY_CODE_RANGE = ('\x00', '\x1f')


class Decoder(object):
    def __init__(self):
        self.hessian_obj_factory = HessianObjectFactory()
        self._refs = []
        self.decoders = {
            'N': self.decode_null,
            'T': self.decode_bool,
            'F': self.decode_bool,
            'I': self.decode_int,
            'Y': self.decode_long,
            'L': self.decode_long,
            'D': self.decode_double,
            '\x5b': self.decode_double,
            '\x5c': self.decode_double,
            '\x5d': self.decode_double,
            '\x5e': self.decode_double,
            '\x5f': self.decode_double,
            #'B': self.decode_binary,
            #'b': self.decode_binary,
            '\x4b': self.decode_date,
            '\x4a': self.decode_date,
            'd': self.decode_date,  # compatible with hessian 1.0
            'V': self.decode_list,
            'S': self.decode_string,
            'M': self.decode_typed_map,
            'H': self.decode_untyped_map,
            'O': self.decode_object,
            'o': self.decode_object_instance,
            '\x51': self.decode_ref,
        }

    def _set_decoder(self, byte_code, decoder_name):
        if not hasattr(self, decoder_name):
            raise Exception('Unknown decoder name: %s' % decoder_name)
        self.decoders[byte_code] = getattr(self, decoder_name)

    def decode(self, buf):
        return self._decode(0, buf)[1]

    def _decode(self, pos, buf):
        tag = buf[pos]
        if tag in self.decoders:
            return self.decoders[tag](pos, buf)
        elif self.is_int(tag):
            return self.decode_int(pos, buf)
        elif self.is_long(tag):
            return self.decode_long(pos, buf)
        elif self.is_string(tag):
            return self.decode_string(pos, buf)
        elif self.is_binary(tag):
            return self.decode_binary(pos, buf)
        else:
            # TODO: decode following code range
            '''
            x30 - x33    # utf-8 string length 0-1023
            x34 - x37    # binary data length 0-1023
            x60 - x6f    # object with direct type
            x70 - x77    # fixed list with direct length
            x78 - x7f    # fixed untyped list with direct length
            '''
            raise Exception("decode error, unknown tag: %r" % tag)

    @staticmethod
    def is_int(tag):
        return (
            (ONE_INT_CODE_RANGE[0] <= tag <= ONE_INT_CODE_RANGE[1]) or
            (TWO_INT_CODE_RANGE[0] <= tag <= TWO_INT_CODE_RANGE[1]) or
            (THREE_INT_CODE_RANGE[0] <= tag <= THREE_INT_CODE_RANGE[1]) or
            tag == 'I'
        )

    @staticmethod
    def is_long(tag):
        return (
            (ONE_LONG_CODE_RANGE[0] <= tag <= ONE_LONG_CODE_RANGE[1]) or
            (TWO_LONG_CODE_RANGE[0] <= tag <= TWO_LONG_CODE_RANGE[1]) or
            (THREE_LONG_CODE_RANGE[0] <= tag <= THREE_LONG_CODE_RANGE[1]) or
            tag == 'Y' or tag == 'L'
        )

    @staticmethod
    def is_string(tag):
        return (
            (SHORT_STRING_CODE_RANGE[0] <= tag <= SHORT_STRING_CODE_RANGE[1])
            or tag == 's' or tag == 'S'
        )

    @staticmethod
    def is_binary(tag):
        return (
            (SHORT_BINARY_CODE_RANGE[0] <= tag <= SHORT_BINARY_CODE_RANGE[1])
            or tag == 's' or tag == 'S'
        )

    def decode_null(self, pos, buf):
        return pos+1, None

    def decode_bool(self, pos, buf):
        return pos+1, buf[pos] == 'T'

    def decode_int(self, pos, buf):
        tag = buf[pos]
        if ONE_INT_CODE_RANGE[0] <= tag <= ONE_INT_CODE_RANGE[1]:
            return pos+1, ord(tag) - 0x90
        elif TWO_INT_CODE_RANGE[0] <= tag <= TWO_INT_CODE_RANGE[1]:
            return pos+2, ((ord(tag) - 0xc8) << 8) + ord(buf[pos+1])
        elif THREE_INT_CODE_RANGE[0] <= tag <= THREE_INT_CODE_RANGE[1]:
            return pos+3, ((ord(tag)-0xd4)<<16) + (ord(buf[pos+1])<<8) + ord(buf[pos+2])
        elif tag == 'I':
            return pos+5, unpack('>l', buf[pos+1:pos+5])[0]
        else:
            raise Exception("decode int error, unknown tag: %r" % tag)

    def decode_long(self, pos, buf):
        tag = buf[pos]
        if ONE_LONG_CODE_RANGE[0] <= tag <= ONE_LONG_CODE_RANGE[1]:
            return pos+1, ord(tag) - 0xe0
        elif TWO_LONG_CODE_RANGE[0] <= tag <= TWO_LONG_CODE_RANGE[1]:
            return pos+2, ((ord(tag)-0xf8)<<8) + ord(buf[pos+1])
        elif THREE_LONG_CODE_RANGE[0] <= tag <= THREE_LONG_CODE_RANGE[1]:
            return pos+3, ((ord(tag)-0x3c)<<16) + (ord(buf[pos+1])<<8) + ord(buf[pos+2])
        elif tag == 'Y':
            return pos+5, unpack('>l', buf[pos+1:pos+5])[0]
        elif tag == 'L':
            return pos+9, unpack('>q', buf[pos+1:pos+9])[0]
        else:
            raise Exception("decode long error, unknown tag: %r" % tag)

    def decode_double(self, pos, buf):
        tag = buf[pos]
        if tag == '\x5b':
            return pos+1, 0.0
        elif tag == '\x5c':
            return pos+1, 1.0
        elif tag == '\x5d':
            return pos+2, float(unpack('>b', buf[pos+1])[0])
        elif tag == '\x5e':
            return pos+3, float(unpack('>h', buf[pos+1:pos+3])[0])
        elif tag == '\x5f':
            return pos+5, unpack('>f', buf[pos+1:pos+5])[0]
        elif tag == 'D':
            return pos+9, unpack('>d', buf[pos+1:pos+9])[0]
        else:
            raise Exception("decode double error, unknown tag: %r" % tag)

    def decode_binary(self, pos, buf):
        tag = buf[pos]
        # TODO: uncompleted
        pass

    def decode_date(self, pos, buf):
        tag = buf[pos]; pos += 1
        if tag == '\x4b':
            return pos+4, MKTIME(unpack('>l', buf[pos:pos+4])[0]*60)
        elif tag == '\x4a' or tag == 'd':
            return pos+8, MKTIME(unpack('>q', buf[pos:pos+8])[0]/1000)
        else:
            raise Exception("decode date error, unknown tag: %r" % tag)

    def decode_list(self, pos, buf):
        tag = buf[pos]; pos += 1
        if tag == 'V':
            pos, _type = self.decode_string(pos, buf)
            pos, length = self.decode_int(pos, buf)

            ret = []
            for i in xrange(length):
                pos, obj = self._decode(pos, buf)
                ret.append(obj)
            return pos, ret
        else:
            raise Exception("decode list error, unknown tag: %r" % tag)

    def read_characters(self, pos, buf, length):
        '''
        read length characters from buf.
        since hessian string '\x02\xe4\xb8\xad\xe6\x96\x87' represents
        2 utf8 characters, we decode '\x02\xe4\xb8' as a string.

        UTF8 characters length:
            00-7F one octet, ascii
            C0-DF two octets
            E0-EF three octets
            F0-F7 four octets
        '''
        begin = pos
        for _ in xrange(length):
            code = buf[pos]
            if code <= '\x7f':
                pos += 1
            elif '\xc0' <= code <= '\xdf':
                pos += 2
            elif '\xe0' <= code <= '\xef':
                pos += 3
            elif '\xf0' <= code <= '\xf7':
                pos += 4
            else:
                raise Exception('Unknown utf8 character: %r' % code)
        return pos, buf[begin:pos]

    def decode_string(self, pos, buf):
        tag = buf[pos]
        pos+= 1
        if SHORT_STRING_CODE_RANGE[0] <= tag <= SHORT_STRING_CODE_RANGE[1]:
            length = ord(tag)
            return self.read_characters(pos, buf, length)
        elif tag == 'S':
            length = unpack('>H', buf[pos:pos+2])[0]
            return self.read_characters(pos+2, buf, length)
        elif tag == 's':  # tag == 's'
            length = unpack('>H', buf[pos:pos+2])[0]
            pos, data = self.read_characters(pos+2, buf, length)
            pos, subdata = self.decode_string(pos, buf)
            return pos, data+subdata
        else:
            raise Exception("decode string error, unknown tag: %r" % tag)

    def decode_untyped_map(self, pos, buf):
        tag = buf[pos]; pos += 1
        ret = {}
        if tag == 'H':
            while buf[pos] != 'z':
                pos, key = self._decode(pos, buf)
                pos, value = self._decode(pos, buf)
                ret[key] = value
            return pos+1, ret
        else:
            raise Exception("decode untyped map error, unknown tag: %r" % tag)

    def decode_typed_map(self, pos, buf):
        tag = buf[pos]; pos += 1
        ret = {}
        if tag == 'M':
            pos, _type = self.decode_string(pos, buf)
            ret['type'] = _type
            ret['body'] = {}
            while buf[pos] != 'z':
                pos, key = self._decode(pos, buf)
                pos, value = self._decode(pos, buf)
                ret['body'][key] = value
            return pos+1, ret
        else:
            raise Exception("decode map error, unknown tag: %r" % tag)

    def decode_object(self, pos, buf):
        tag = buf[pos]; pos += 1
        if tag == 'O':
            pos, _class = self.decode_string(pos, buf)
            pos, field_num = self.decode_int(pos, buf)
            fields = []
            for i in xrange(field_num):
                pos, field = self.decode_string(pos, buf)
                fields.append(field)
            self.hessian_obj_factory.create_object(_class, fields)

            pos, obj = self.decode_object_instance(pos, buf)
            return pos, obj
        else:
            raise Exception("decode map error, unknown tag: %r" % tag)

    def decode_object_instance(self, pos, buf):
        tag = buf[pos]; pos += 1
        ret = []
        if tag == 'o':
            self._refs.append(None)  # occupy the position
            ref_id = len(self._refs) - 1   # record the position
            # decode ref id
            tag = buf[pos]
            ref = 0
            if self.is_int(tag):
                pos, ref = self.decode_int(pos, buf)

            values = []
            field_num = self.hessian_obj_factory.object_field_num(ref)
            for i in xrange(field_num):
                pos, value = self._decode(pos, buf)
                values.append(value)
            obj = self.hessian_obj_factory.create_instance(ref, values)
            self._refs[ref_id] = obj
            return pos, obj
        else:
            raise Exception("decode map error, unknown tag: %r" % tag)

    def decode_ref(self, pos, buf):
        tag = buf[pos]; pos += 1
        if tag == '\x51':
            pos, ref = self.decode_int(pos, buf)
        elif tag == '\x4a':
            ref = ord(buf[pos]); pos += 1
        elif tag == '\x4b':
            ref = (ord(buf[pos]) << 8) + ord(buf[pos+1]); pos += 2
        else:
            raise Exception("decode ref error, unknown tag: %r" % tag)
        return pos, self._refs[ref]
