# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/internal.py -- non-public methods for internal module consumption
#
# This software is for POSIX compliant systems only.
import errno
from . import FSQCoerceError

_COERCE_THESE_TOO = (int,float,)

def coerce_unicode(s, encoding='utf8'):
    if isinstance(s, unicode):
        return s
    try:
        return unicode(s, encoding=encoding)
    except (UnicodeEncodeError, UnicodeDecodeError, ), e:
        raise FSQCoerceError(errno.EINVAL, e.message)
    except TypeError, e:
        if s.__class__ in _COERCE_THESE_TOO:
            try:
                return unicode(s)
            except Exception, e:
                raise FSQCoerceError(errno.EINVAL, e.message)

        raise FSQCoerceError(errno.EINVAL, e.message)
