# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/v1.py -- provides version 1 API function: enqueue
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
from .. import sreenqueue

def enqueue(item_id, src_queue, hosts, data, debug=False):
    if isinstance(hosts, basestring):
        hosts = (hosts,)
    if data:
        return sreenqueue(item_id, data, src_queue, hosts=hosts, debug=debug)
    return sreenqueue(item_id, '', src_queue, hosts=hosts, debug=debug)

#libexec/fsq/jsonrpcd.py will load all functions in __all__
__all__ = [ 'enqueue', ]
