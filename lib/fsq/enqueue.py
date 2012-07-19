# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/enqueue.py -- provides enqueueing functions: enqueue, senqueue,
#                   venqueue, vsenqueue
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import errno
import os
import datetime
import socket

from cStringIO import StringIO
from contextlib import closing

from . import FSQEnqueueError, FSQ_ITEM_USER, FSQ_ITEM_GROUP, FSQ_ITEM_MODE,\
              FSQ_TIMEFMT, path as fsq_path, construct
from .internal import rationalize_file, wrap_io_os_err, fmt_time,\
                      coerce_unicode, uid_gid

# TODO: provide an internal/external streamable queue item object use that
#       instead of this for the enqueue family of functions
#       make a queue item from args, return a file

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
def enqueue(trg_queue, item_f, *args, **kwargs):
    '''Enqueue the contents of a file, or file-like object, file-descriptor or
       the contents of a file at an address (e.g. '/my/file') queue with
       arbitrary arguments, enqueue is to venqueue what printf is to vprintf
    '''
    return venqueue(trg_queue, item_f, args, **kwargs)

def senqueue(trg_queue, item_s, *args, **kwargs):
    '''Enqueue a string, or string-like object to queue with arbitrary
       arguments, senqueue is to enqueue what sprintf is to printf, senqueue
       is to vsenqueue what sprintf is to vsprintf.
    '''
    return vsenqueue(trg_queue, item_s, args, **kwargs)

def venqueue(trg_queue, item_f, args, user=None, group=None, mode=None):
    '''Enqueue the contents of a file, or file-like object, file-descriptor or
       the contents of a file at an address (e.g. '/my/file') queue with
       an argument list, venqueue is to enqueue what vprintf is to printf

       If entropy is passed in, failure on duplicates is raised to the caller,
       if entropy is not passed in, venqueue will increment entropy until it
       can create the queue item.
    '''
    # setup defaults
    trg_fd = trg = name = None
    user = FSQ_ITEM_USER if user is None else user
    group = FSQ_ITEM_GROUP if group is None else group
    mode = FSQ_ITEM_MODE if mode is None else mode
    now = fmt_time(datetime.datetime.now(), FSQ_TIMEFMT)
    pid = coerce_unicode(os.getpid())
    host = coerce_unicode(_HOSTNAME)
    tries = coerce_unicode(0)
    entropy = _mkentropy(pid, now, host)

    # open source file
    with closing(rationalize_file(item_f)) as src_file:
        # get low, so we can use some handy options; man 2 open
        try:
            item_name = construct(( now, entropy, pid, host,
                                    tries, ) + tuple(args))
            tmp_name = os.path.join(fsq_path.tmp(trg_queue), item_name)
            trg_fd = os.open(tmp_name, os.O_WRONLY|os.O_CREAT|os.O_EXCL, mode)
        except (OSError, IOError, ), e:
            raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
        try:
            if user is not None or group is not None:
                # set user/group ownership for file; man 2 fchown
                os.fchown(trg_fd, *uid_gid(user, group, fd=trg_fd))
            with closing(os.fdopen(trg_fd, 'wb', 1)) as trg_file:
                # i/o time ... assume line-buffered
                while True:
                    line = src_file.readline()
                    if not line:
                        break
                    trg_file.write(line)
                # flush buffers, and force write to disk pre mv.
                trg_file.flush()
                os.fsync(trg_file.fileno())

                # hard-link into queue, unlink tmp, failure case here leaves
                # cruft in tmp, but no race condition into queue
                os.link(tmp_name, os.path.join(fsq_path.item(trg_queue,
                                                             item_name)))
                os.unlink(tmp_name)

                # return the queue item id (filename)
                return item_name
        except (OSError, IOError, ), e:
            os.close(trg_fd)
            os.unlink(trg)
            raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
        except Exception, e:
            try:
                os.close(trg_fd)
            except (OSError, IOError, ), e:
                if errno != errno.EBADF:
                    raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
            try:
                os.unlink(name)
            except OSError, e:
                if e.errno != errno.ENOENT:
                   raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
            if isinstance(e, OSError) or isinstance(e, IOError):
                raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
            raise e

def vsenqueue(trg_queue, item_s, args, **kwargs):
    '''Enqueue a string, or string-like object to queue with arbitrary
       arguments, vsenqueue is to venqueue what vsprintf is to vprintf,
       vsenqueue is to senqueue what vsprintf is to sprintf.
    '''
    return venqueue(trg_queue, StringIO(item_s), args, **kwargs)
