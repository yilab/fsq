# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/v1.py -- provides version 1 API function: enqueue
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import sys
from .. import sreenqueue

def enqueue(item_id, src_queue, hosts, data):
    if isinstance(hosts, basestring):
        hosts = (hosts,)
    if not data:
        data = ''
    print >> sys.stdout, sreenqueue(item_id, data, src_queue, hosts=hosts)

#libexec/fsq/jsonrpcd.py will load all functions in __all__
__all__ = [ 'enqueue', ]
