#-*- coding:utf8 -*-

'''
Hessian2.0 encoder implementation in python.

According to http://hessian.caucho.com/doc/hessian-serialization.html.
'''

import json
from datetime import datetime


class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        return o.__dict__


class HessianObject(object):
    def __init__(self, _class, attrs):
        self._class = _class
        self.attrs = attrs

    def representation(self):
        return {
            '_class': self._class,
            'attrs': self.attrs,
        }

    def __str__(self):
        return json.dumps(self.representation(), cls=JsonEncoder,
                          ensure_ascii=False, indent=2)


class TypedMap(object):
    def __init__(self, _type, val):
        self._type = _type
        self.val = val


class DoubleType(object):
    def __init__(self, val):
        self._class = 'double'
        self.value = val


class HessianObjectFactory(object):
    def __init__(self):
        self.objects = []
        self.object_fields = {}

    def create_object(self, _class, fields):
        self.objects.append(_class)
        self.object_fields[_class] = fields

    def object_field_num(self, ref):
        return len(self.object_fields[self.objects[ref]])

    def create_instance(self, ref, values):
        assert self.object_field_num(ref) == len(values)
        _class = self.objects[ref]
        val = dict(zip(self.object_fields[_class], values))
        return HessianObject(_class, val)
