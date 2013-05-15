# fsq -- a python ligbrary for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/configure.py -- provides queue configuration functions: down, up, is_down
#                     trigger, untrigger, trigger_pull, down_host, up_host,
#                     host_is_down, host_trigger, host_untrigger,
#                     host_trigger_pull, hosts
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno

from . import constants as _c, path as fsq_path, FSQConfigError,\
              FSQTriggerPullError, FSQError
from .internal import uid_gid, wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
# try to delete a file, and raise a wrapped error
_NSQ = u'no such queue: {0}'
def _raise(path, e):
    if e.errno == errno.ENOENT:
        raise FSQConfigError(e.errno, _NSQ.format(path))
    raise FSQConfigError(e.errno, wrap_io_os_err(e))

def _dflts(user, group, mode):
    user = _c.FSQ_ITEM_USER if user is None else user
    group = _c.FSQ_ITEM_GROUP if group is None else group
    mode = _c.FSQ_ITEM_MODE if mode is None else mode
    return ( user, group, mode, )

def _cleanup(path, e):
    try:
        os.unlink(path)
    except (OSError, IOError, ), err:
        if err.errno != errno.ENOENT:
            raise FSQConfigError(err.errno, wrap_io_os_err(err))
    _raise(path, e)

def _queue_ok(q_path):
    # TODO: refactor to use fopen / fstatat, python doesn't support this
    try:
        os.stat(q_path)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQConfigError(e.errno, _NSQ.format(q_path))
        raise FSQConfigError(e.errno, wrap_io_os_err(e))

####### EXPOSED METHODS #######
def down(queue, user=None, group=None, mode=None, host=None) :
    '''Down a queue, by creating a down file'''
    # default our owners and mode
    user, group, mode = _dflts(user, group, mode)
    down_path = fsq_path.down(queue, host=host)
    fd = None
    created = False
    try:
        # try to guarentee creation
        try:
            fd = os.open(down_path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, mode)
            created = True
        except (OSError, IOError, ), e:
            if e.errno != errno.EEXIST:
                raise e
            fd = os.open(down_path, os.O_CREAT|os.O_WRONLY, mode)
        if user is not None or group is not None:
            os.fchown(fd, *uid_gid(user, group, fd=fd))
        if not created:
            os.fchmod(fd, mode)
    except (OSError, IOError, ), e:
        if created:
            _cleanup(down_path, e)
        _raise(down_path, e)
    finally:
        if fd is not None:
            os.close(fd)

def up(queue, host=None):
    '''Up a queue, by removing a down file -- if a queue has no down file,
       this function is a no-op.'''
    down_path = fsq_path.down(queue, host=host)
    _queue_ok(os.path.dirname(down_path))
    try:
        os.unlink(down_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise FSQConfigError(e.errno, wrap_io_os_err(e))

def is_down(queue, host=None):
    '''Returns True if queue is down, False if queue is up'''
    down_path = fsq_path.down(queue, host=host)
    _queue_ok(os.path.dirname(down_path))
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

def trigger(queue, user=None, group=None, mode=None, trigger=_c.FSQ_TRIGGER):
    '''Installs a trigger for the specified queue.'''
    # default our owners and mode
    user, group, mode = _dflts(user, group, mode)
    trigger_path = fsq_path.trigger(queue, trigger=trigger)
    created = False
    try:
        # mkfifo is incapable of taking unicode, coerce back to str
        try:
            os.mkfifo(trigger_path.encode(_c.FSQ_CHARSET), mode)
            created = True
        except (OSError, IOError, ), e:
            # if failure not due to existence, rm and bail
            if e.errno != errno.EEXIST:
                raise e

        # don't open and fchown here, as opening WRONLY without an open
        # reading fd will hang, opening RDONLY will zombie if we don't
        # flush, and intercepts triggers meant to go elsewheres
        os.chmod(trigger_path, mode)
        if user is not None or group is not None:
            os.chown(trigger_path, *uid_gid(user, group, path=trigger_path))
    except (OSError, IOError, ), e:
        # only rm if we created and failed, otherwise leave it and fail
        if created:
            _cleanup(trigger_path, e)
        _raise(trigger_path, e)

def untrigger(queue, trigger=_c.FSQ_TRIGGER):
    '''Uninstalls the trigger for the specified queue -- if a queue has no
       trigger, this function is a no-op.'''
    trigger_path = fsq_path.trigger(queue, trigger=trigger)
    _queue_ok(os.path.dirname(trigger_path))
    try:
        os.unlink(trigger_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise FSQConfigError(e.errno, wrap_io_os_err(e))

def trigger_pull(queue, ignore_listener=False, trigger=_c.FSQ_TRIGGER):
    '''Write a non-blocking byte to a trigger fifo, to cause a triggered
       scan'''
    fd = None
    trigger_path = fsq_path.trigger(queue, trigger=trigger)
    _queue_ok(os.path.dirname(trigger_path))
    try:
        fd = os.open(trigger_path,
                     os.O_NDELAY|os.O_NONBLOCK|os.O_APPEND|os.O_WRONLY)
        os.write(fd, '\0')
    except (OSError, IOError, ), e:
        if e.errno != errno.ENXIO:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                raise FSQTriggerPullError(e.errno, wrap_io_os_err(e))
        elif not ignore_listener:
            raise FSQTriggerPullError(e.errno, u'No listener for:'\
                                      u' {0}'.format(trigger_path))
    finally:
        if fd is not None:
            os.close(fd)

def down_host(trg_queue, host, user=None, group=None, mode=None):
    ''' Down a host queue by creating a down file in the host queue
        directory '''
    down(trg_queue, user=user, group=group, mode=mode, host=host)

def up_host(trg_queue, host):
    '''Idempotently uninstall a queue, should you want to subvert FSQ_ROOT
       settings, merely pass in an abolute path'''
    # immediately down the queue
    up(trg_queue, host=host)

def host_is_down(trg_queue, host):
    '''Returns True if host queue is down, False if queue is up'''
    return is_down(trg_queue, host)

def host_trigger(trg_queue, user=None, group=None, mode=None):
    '''Installs a host trigger for the specified queue.'''
    trigger(trg_queue, user=user, group=group, mode=mode,
            trigger=_c.FSQ_HOSTS_TRIGGER)

def host_untrigger(trg_queue):
    '''Uninstalls the host trigger for the specified queue -- if a queue has no
       trigger, this function is a no-op.'''
    untrigger(trg_queue, trigger=_c.FSQ_HOSTS_TRIGGER)

def host_trigger_pull(trg_queue, ignore_listener=False):
    '''Write a non-blocking byte to a host trigger fifo, to cause a triggered
       scan'''
    trigger_pull(trg_queue, ignore_listener=ignore_listener,
                 trigger=_c.FSQ_HOSTS_TRIGGER)
