# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/internal.py -- non-public methods for internal module consumption
#
# This software is for POSIX compliant systems only.
import errno
from . import FSQCoerceError, FSQEncodeError

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

def encodeseq_delimiter(delimiter, encodeseq):
    delimiter = coerce_unicode(delimiter)
    encodeseq = coerce_unicode(encodeseq)
    if 1 != len(encodeseq):
        raise FSQEncodeError(errno.EINVAL, u'encode sequence must be 1'\
                             u' character, not {0}'.format(len(encodeseq)))
    elif delimiter == encodeseq:
        raise FSQEncodeError(errno.EINVAL, u'delimiter and encoding may not'\
                             u' be the same: both: {0}'.format(encodeseq))
    return delimiter, encodeseq
