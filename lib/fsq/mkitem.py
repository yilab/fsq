# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/enqueue.py -- provides FS-level interfaces for making queue item files
#                   from arguments, provides: mkitem
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno
import socket
import datetime

from . import FSQ_TIMEFMT, FSQ_ITEM_USER, FSQ_ITEM_GROUP, FSQ_ITEM_MODE,\
              construct, FSQEnqueueError, FSQTimeFmtError
from .internal import coerce_unicode, uid_gid, wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
_HOSTNAME = socket.gethostname()
_ENTROPY_PID = None
_ENTROPY_TIME = None
_ENTROPY_HOST = None
_ENTROPY = 0

# sacrifice a lot of complexity for a little statefullness
def _mkentropy(pid, now, host):
    global _ENTROPY_PID, _ENTROPY_TIME, _ENTROPY_HOST, _ENTROPY
    if _ENTROPY_PID == pid and _ENTROPY_TIME == now and _ENTROPY_HOST == host:
        _ENTROPY += 1
    else:
        _ENTROPY_PID = pid
        _ENTROPY_TIME = now
        _ENTROPY_HOST = host
        _ENTROPY = 0

    return _ENTROPY

####### EXPOSED METHODS #######
def mkitem(trg_path, args, user=None, group=None, mode=None, now=None,
           pid=None, host=None, tries=None, rename_src=None, entropy=None):
    '''mkitem is the guts of how queue item filenames are reserved and
       atomically created.  rename_src exists to provide the ability to
       rename a source file into trg_path with args, providing the facility
       to atomically finish/fail queue items.  rename_src is not used to
       commit from tmp to queue, link/unlink is prefered to avoid any
       possibility (should be none if everything is to spec) of collision
       in queue. rename and link require all queue directories to exist
       on the same partition.'''
    trg_fd = trg = name = None

    # default user, group and mode
    user = FSQ_ITEM_USER if user is None else user
    group = FSQ_ITEM_GROUP if group is None else group
    mode = FSQ_ITEM_MODE if mode is None else mode

    # default now to now(), format to FSQ_TIMEFMT
    now = datetime.datetime.now() if now is None else now
    try:
        now = coerce_unicode(now.strftime(FSQ_TIMEFMT))
    except AttributeError, e:
        raise TypeError(u'now must be a datetime, date, time, or other type'\
                        u' supporting strftime, not {0}'.format(
                        now.__class__.__name__))
    except TypeError, e:
        raise TypeError(u'timefmt must be a string or read-only buffer,'\
                        ' not {0}'.format(FSQ_TIMEFMT.__class__.__name__))
    except ValueError, e:
        raise FSQTimeFmtError(errno.EINVAL, u'invalid fmt for strftime:'\
                              ' {0}'.format(FSQ_TIMEFMT))
    # default pid to os.getpid()
    pid = coerce_unicode(os.getpid() if pid is None else pid)
    # default host to socket.gethostname()
    host = coerce_unicode(_HOSTNAME if host is None else host)
    # default tries to 0
    tries = coerce_unicode(0 if tries is None else tries)
    # default entropy ...
    if entropy is None:
        entropy = _mkentropy(pid, now, host)
    entropy = coerce_unicode(entropy)

    # get low, so we can use some handy options; man 2 open
    try:
        name = construct((now, entropy, pid, host, tries, ) + tuple(args))
        trg = os.path.join(trg_path, name)
        if rename_src:
            os.rename(rename_src, trg)
            return trg, None
        else:
            trg_fd = os.open(trg, os.O_WRONLY|os.O_CREAT|os.O_EXCL, mode)
    except (OSError, IOError, ), e:
        raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
    try:
        if user is not None or group is not None:
            # set user/group ownership for file; man 2 fchown
            os.fchown(trg_fd, *uid_gid(user, group, fd=trg_fd))
        # return something that is safe to close in scope
        return trg, os.fdopen(os.dup(trg_fd), 'wb', 1)
    except (OSError, IOError, ), e:
        os.unlink(trg)
        raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
    # we return a file on a dup'ed fd, always close original fd
    finally:
        if trg_fd is not None:
            os.close(trg_fd)
