# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/list.py -- provides directory listing functions: hosts, queue
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os

from . import constants as _c, path as fsq_path, FSQHostsError, FSQPathError
from .internal import wrap_io_os_err

def _list_dir(root, ex):
    try:
        return tuple(os.listdir(root))
    except (OSError, IOError), e:
        raise ex(e.errno, wrap_io_os_err(e))

def hosts(trg_queue):
    ''' returns a tuple of host queues '''
    return _list_dir(fsq_path.hosts(trg_queue), FSQHostsError)

def queues():
    ''' returns a tuple of queues '''
    return _list_dir(_c.FSQ_ROOT, FSQPathError)
