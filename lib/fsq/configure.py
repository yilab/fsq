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

from . import FSQ_ITEM_USER, FSQ_ITEM_GROUP, FSQ_ITEM_MODE, path as fsq_path,\
              FSQConfigError, FSQTriggerPullError
from .internal import uid_gid, wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
# try to delete a file, and raise a wrapped error
def _cleanup(path, e):
    try:
        os.unlink(path)
    except (OSError, IOError, ), err:
        if err.errno != errno.ENOENT:
            raise FSQConfigError(err.errno, wrap_io_os_err(err))
    if e.errno == errno.ENOENT:
        raise FSQConfigError(e.errno, u'no such queue: {0}'.format(path))
    raise FSQConfigError(e.errno, wrap_io_os_err(e))

####### EXPOSED METHODS #######
def down(queue, user=None, group=None, mode=None):
    '''Down a queue, by creating a down file'''
    # default our owners and mode
    user = FSQ_ITEM_USER if user is None else user
    group = FSQ_ITEM_GROUP if group is None else group
    mode = FSQ_ITEM_MODE if mode is None else mode

    # construct the down path, and install
    down_path = fsq_path.down(queue)
    fd = None
    try:
        fd = os.open(down_path, os.O_CREAT|os.O_WRONLY, mode)
        if user is not None or group is not None:
            os.fchown(fd, *uid_gid(user, group, fd=fd))
    except (OSError, IOError, ), e:
        _cleanup(down_path, e)
    finally:
        if fd is not None:
            os.close(fd)

def up(queue):
    '''Up a queue, by removing a down file -- if a queue has no down file,
       this function is a no-op.'''
    down_path = fsq_path.down(queue)
    try:
        os.unlink(down_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise FSQConfigError(e.errno, wrap_io_os_err(e))

def is_down(queue):
    '''Returns True if queue is down, False if queue is up'''
    if not down:
        return False
    down_path = fsq_path.down(queue)
    # use stat instead of os.path.exists because non-ENOENT errors are a
    # configuration issue, and should raise exeptions (e.g. if you can't
    # access due to permissions, we want to raise EPERM, not return False)
    try:
        os.stat(down_path)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            return False
        raise FSQConfigError(e.errno, wrap_io_os_err(e))
    return True

def trigger(queue, user=None, group=None, mode=None):
    '''Installs a trigger for the specified queue.'''
    mode = FSQ_ITEM_MODE if mode is None else mode
    trigger_path = fsq_path.trigger(queue)
    fd = None
    try:
        os.mkfifo(trigger_path, mode)
        if user is not None or group is not None:
            fd = os.open(trigger_path, os.O_WRONLY)
            os.fchown(fd, *uid_gid(user, group, fd=fd))
    except (OSError, IOError, ), e:
        _cleanup(trigger_path, e)
    finally:
        if fd is not None:
            os.close(fd)

def untrigger(queue):
    '''Uninstalls the trigger for the specified queue -- if a queue has no
       trigger, this function is a no-op.'''
    trigger_path = fsq_path.trigger(queue)
    try:
        os.unlink(trigger_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise FSQConfigError(e.errno, wrap_io_os_err(e))

def trigger_pull(queue, ignore_listener=False):
    '''Write a non-blocking byte to a trigger fifo, to cause a triggered
       scan'''
    fd = None
    trigger_path = fsq_path.trigger(queue)
    try:
        fd = os.open(trigger_path,
                     os.O_NDELAY|os.O_NONBLOCK|os.O_APPEND|os.O_WRONLY)
        os.write(fd, '\0')
    except (OSError, IOError, ), e:
        if not ignore_listener and e.errno == errno.ENODEV:
            raise FSQTriggerPullError(e.errno, u'No listener for:'\
                                      u' {0}'.format(trigger_path))
        if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
            raise FSQTriggerPullError(e.errno, wrap_io_os_err(e))
    finally:
        if fd is not None:
            os.close(fd)
