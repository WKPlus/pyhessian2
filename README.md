pyhessian2 is implemented for serialize and deserialize data in hessian2 protocol.

##Usage

###Encoding
----

```
from pyhessian2 import HessianObject, Encoder
attrs = {
    "name": "xx",
    "age": 20,
}
obj = HessianObject("com.xx.person", attrs)
data = Encoder().encode(obj)
print "%r" % data
```


###Decoding
----

```
from pyhessian2 import Decoder
data = ...  # a hessian bytes data
obj = Decoder().decoder(data)  # get a Hessianobject instance
print obj  # print json serialized data
```
