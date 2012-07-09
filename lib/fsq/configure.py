# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/configure.py -- provides queue configuration functions: down, up
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno

from . import FSQ_ROOT, FSQ_DOWN, FSQ_ITEM_USER, FSQ_ITEM_GROUP,\
              FSQ_ITEM_MODE, path as fsq_path, FSQConfigError
from .internal import coerce_unicode, uid_gid, wrap_io_os_err

def down(queue, root=FSQ_ROOT, down=FSQ_DOWN, user=FSQ_ITEM_USER,
         group=FSQ_ITEM_GROUP, mode=FSQ_ITEM_MODE):
    '''Down a queue, by creating a down file'''
    down_path = fsq_path.down(queue, root=root, down=down)
    fd = None
    try:
        fd = os.open(down_path, os.O_CREAT|os.O_WRONLY, mode)
        if user is not None or group is not None:
            os.fchown(fd, *uid_gid(user, group, fd=fd))
    except (OSError, IOError, ), e:
        try:
            os.unlink(down_path)
        except (OSError, IOError, ), err:
            if err.errno != errno.ENOENT:
                raise FSQConfigError(err.errno, wrap_io_os_err(err))
        if e.errno == errno.ENOENT:
            raise FSQConfigError(e.errno, u'no such queue: {0}'.format(queue))
        raise FSQConfigError(e.errno, wrap_io_os_err(e))
    finally:
        if fd is not None:
            os.close(fd)

def up(queue, root=FSQ_ROOT, down=FSQ_DOWN):
    '''Up a queue, by removing a down file -- if a queue has no down file,
       this function is a no-op.'''
    down_path = fsq_path.down(queue, root=root, down=down)
    try:
        os.unlink(down_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise FSQConfigError(e.errno, wrap_io_os_err(e))

def is_down(queue, root=FSQ_ROOT, down=FSQ_DOWN):
    '''Returns True if queue is down, False if queue is up'''
    if not down:
        return False
    down_path = fsq_path.down(queue, root=root, down=down)
    try:
        os.stat(down_path)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            return False
        raise FSQConfigError(e.errno, wrap_io_os_err(e))
    return True
