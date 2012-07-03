# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/internal.py -- non-public methods for internal module consumption
#
# This software is for POSIX compliant systems only.
import errno
from . import FSQCoerceError

def coerce_unicode(s, encoding='utf8'):
    if isinstance(s, unicode):
        return s
    try:
        return unicode(s, encoding=encoding)
    except (TypeError, UnicodeEncodeError, UnicodeDecodeError, ), e:
        raise FSQCoerceError(errno.EINVAL, e.message)
