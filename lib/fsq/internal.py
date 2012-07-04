# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/internal.py -- non-public methods for internal module consumption
#
# This software is for POSIX compliant systems only.
import os
import errno
import pwd
import grp

from . import FSQCoerceError, FSQEncodeError, FSQEnvError

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
_COERCE_THESE_TOO = (int,float,)

####### EXPOSED METHODS #######
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

def delimiter_encodeseq(delimiter, encodeseq):
    '''Coerce dlimiter and encodeseq to unicode and verify that they are not
       the same'''
    delimiter = coerce_unicode(delimiter)
    encodeseq = coerce_unicode(encodeseq)
    if 1 != len(encodeseq):
        raise FSQEncodeError(errno.EINVAL, u'encode sequence must be 1'\
                             u' character, not {0}'.format(len(encodeseq)))
    elif delimiter == encodeseq:
        raise FSQEncodeError(errno.EINVAL, u'delimiter and encoding may not'\
                             u' be the same: both: {0}'.format(encodeseq))
    return delimiter, encodeseq

def uid_gid(user, group):
    '''Get uid and gid from either uid/gid, user name/group name, or from the
       environment of the callig process'''
    type_msg = u'{0} must be a string or integer, not: {1}'
    nosuch_msg = u'no such {0}: {1}'
    if user is None:
        user = os.getuid()
    if group is None:
        group = os.getgid()
    try:
        user = int(user)
    except ValueError, e:
        try:
            user = pwd.getpwnam(user).pw_uid
        except TypeError, e:
            raise TypeError(type_msg.format(u'user', user.__class__.__name__))
        except KeyError, e:
            raise FSQEnvError(errno.EINVAL, nosuch_msg.format(u'user', user))
    try:
        gid = int(group)
    except ValueError, e:
        try:
            group = grp.getgrnam(group).gr_gid
        except TypeError, e:
            raise TypeError(type_msg.format(u'group',
                            group.__class__.__name__))
        except KeyError, e:
            raise FSQEnvError(errno.EINVAL, nosuch_msg.format(u'group',
                              group))

    return user, group

def rationalize_file(item_f):
    '''FSQ attempts to treat all file-like things as line-buffered as an
       optimization to the average case.  rationalize_file will handle file
       objects, buffers, raw file-descriptors, sockets, and string
       file-addresses, and will return a file object that can be safely closed
       in FSQ scope without closing the file in the bounding caller.'''
    # file, TmpFile, socket, etc ...
    if hasattr(item_f, 'fileno'):
        copy = os.fdopen(os.dup(item_f.fileno()))
        # explicitely decriment ref count here
        del item_f
        return copy
    # StringIO, cStringIO, etc ...
    elif hasattr(item_f, 'readline'):
        return item_f
    # raw file descriptor -- e.g. output of pipe
    elif isinstance(item_f, int):
        return os.fdopen(os.dup(item_f))

    # try to open, read+binary, line-buffered
    return open(coerce_unicode(item_f), 'rb', 1)

def wrap_io_os_err(e):
    '''Formats IO and OS error messages for wrapping in FSQExceptions'''
    msg = ''
    if e.strerror:
        msg = e.strerror
    if e.message:
        msg = ' '.join([e.message, msg])
    if e.filename:
        msg = ': '.join([msg, e.filename])
    return msg
