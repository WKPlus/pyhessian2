pyhessian2 is implemented for serialize and deserialize data in hessian2 protocol.

Note, there are some significant differences between the master and 3.1.5 branch:
   * master 
      * implemented in accordance with [the hessian2 serialization protocol draft](http://hessian.caucho.com/doc/hessian-serialization.html)
      * not fully tested
      * published to pypi with version 2.0.0+
   * 3.1.5 
      * implemented in accordance with [the java implementation 3.1.5](http://hessian.caucho.com/#Java)
      * fully tested
      * published to pypi with version 1.0.0+


## Usage

### Encoding
----

```python
from pyhessian2 import HessianObject, Encoder
attrs = {
    "name": "xx",
    "age": 20,
}
obj = HessianObject("com.xx.person", attrs)
data = Encoder().encode(obj)
print "%r" % data
```


### Decoding
----

```python
from pyhessian2 import Decoder
data = ...  # a hessian bytes data
obj = Decoder().decoder(data)  # get a Hessianobject instance
print obj  # print json serialized data
```
