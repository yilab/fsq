# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
#
# fsq/construct.py -- provides path construction convenience functions: tmp,
#                     queue, done, fail, down
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno

from .internal import coerce_unicode
from . import constants as _c, FSQPathError

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
_ILLEGAL_NAMES=('.', '..', )

def _path(queue, extra=None, root=_c.FSQ_ROOT):
    args = [coerce_unicode(root, _c.FSQ_CHARSET), valid_name(queue)]
    if extra is not None:
        args.append(valid_name(extra))
    return os.path.join(*args)

####### EXPOSED METHODS #######
def valid_name(name):
    name = coerce_unicode(name, _c.FSQ_CHARSET)
    if name in _ILLEGAL_NAMES or 0 <= name.find(os.path.sep):
        raise FSQPathError(errno.EINVAL, u'illegal path name:'\
                                  u' {0}'.format(name))
    return name

def base(p_queue, root=_c.FSQ_ROOT):
    return _path(p_queue, root=root)

def tmp(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the tmp dir for a queue'''
    return _path(p_queue, _c.FSQ_TMP, root=root)

def queue(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the queue dir for a queue'''
    return _path(p_queue, _c.FSQ_QUEUE, root=root)

def fail(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the fail dir for a queue'''
    return _path(p_queue, _c.FSQ_FAIL, root=root)

def done(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the done dir for a queue'''
    return _path(p_queue, _c.FSQ_DONE, root=root)

def down(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the down file for a queue'''
    return _path(p_queue, _c.FSQ_DOWN, root=root)

def hosts(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to the down file for a queue'''
    return _path(p_queue, _c.FSQ_HOSTS, root=root)

def item(p_queue, queue_id, root=_c.FSQ_ROOT):
    '''Construct a path to a queued item'''
    return os.path.join(_path(p_queue, _c.FSQ_QUEUE, root=root),
                        valid_name(queue_id))

def trigger(p_queue, root=_c.FSQ_ROOT):
    '''Construct a path to a trigger (FIFO)'''
    return _path(p_queue, _c.FSQ_TRIGGER, root=root)
