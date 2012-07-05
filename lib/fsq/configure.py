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

from . import FSQ_ROOT, FSQ_DOWN, FSQ_USER, FSQ_GROUP, FSQ_MODE,\
              path as fsq_path, FSQConfigError
from .internal import coerce_unicode, uid_gid

def down(queue, root=FSQ_ROOT, down=FSQ_DOWN, user=FSQ_USER, group=FSQ_GROUP,
         mode=FSQ_MODE):
    '''Down a queue, by creating a down file'''
    down_path = fsq_path.down(queue, root=root, down=down)
    fd = None
    try:
        fd = os.open(down_path, os.O_CREAT|os.O_WRONLY, mode)
        os.fchown(fd, *uid_gid(user, group))
    except (OSError, IOError, ), e:
        try:
            os.unlink(trg)
        except (OSError, IOError, ), err:
            if err.errno != errno.ENOENT:
                raise FSQConfigError(err.errno, wrap_io_os_err(err))
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
