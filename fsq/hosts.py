# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/hosts.py -- provides host functions: hosts
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno

from . import path as fsq_path, FSQHostsError, FSQError
from .internal import wrap_io_os_err

def hosts(trg_queue):
    root = fsq_path.hosts(trg_queue)
    try:
        return tuple(os.listdir(root))
    except (OSError, IOError), e:
        if e.errno == errno.ENOENT:
            raise FSQHostsError(e.errno, u'no such host:'\
                               u' {0}'.format(root))
        elif isinstance(e, FSQError):
            raise e
        raise FSQHostsError(e.errno, wrap_io_os_err(e))

