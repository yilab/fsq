# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/hosts.py -- provides host functions: hosts... TODO add more
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno

from . import constants as _c, FSQHostsError, FSQError
from .internal import wrap_io_os_err

def hosts(trg_queue):
    try:
        host = u'/'.join([ _c.FSQ_ROOT, trg_queue, _c.FSQ_HOSTS ])
        return tuple(os.listdir(host))
    except (OSError, IOError), e:
        if e.errno == errno.ENOENT:
            raise FSQHostsError(e.errno, u'no such host:'\
                               u' {0}'.format(host))
        elif isinstance(e, FSQError):
            raise e
        raise FSQHostsError(e.errno, wrap_io_os_err(e))
