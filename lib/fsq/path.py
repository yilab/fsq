# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
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

def _path(queue, extra):
    return os.path.join(coerce_unicode(_c.FSQ_ROOT), valid_name(queue),
                        valid_name(extra))

####### EXPOSED METHODS #######
def valid_name(name):
    name = coerce_unicode(name)
    if name in _ILLEGAL_NAMES or 0 <= name.find(os.path.sep):
        raise FSQPathError(errno.EINVAL, u'illegal path name:'\
                                  u' {0}'.format(name))
    return name

def base(p_queue):
    return _path(p_queue, u'')

def tmp(p_queue):
    '''Construct a path to the tmp dir for a queue'''
    return _path(p_queue, _c.FSQ_TMP)

def queue(p_queue):
    '''Construct a path to the queue dir for a queue'''
    return _path(p_queue, _c.FSQ_QUEUE)

def fail(p_queue):
    '''Construct a path to the fail dir for a queue'''
    return _path(p_queue, _c.FSQ_FAIL)

def done(p_queue):
    '''Construct a path to the done dir for a queue'''
    return _path(p_queue, _c.FSQ_DONE)

def down(p_queue):
    '''Construct a path to the down file for a queue'''
    return _path(p_queue, _c.FSQ_DOWN)

def item(p_queue, queue_id):
    '''Construct a path to a queued item'''
    return os.path.join(_path(p_queue, _c.FSQ_QUEUE), queue_id)

def trigger(p_queue):
    '''Construct a path to a trigger (FIFO)'''
    return _path(p_queue, _c.FSQ_TRIGGER)
