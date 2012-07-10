# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/__init__.py -- wraps fsq in a bow.
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
#
# TODO: when we get to locking, the proper method for BSD systems
# is to open with:
#
#    O_EXLOCK
#
# the proper method on Linux systems is:
#
#    # f = open(...)
#    flock(f.fileno(), LOCK_EX|LOCK_NB)
#
# although the latter will always work, the former is simpler.


# ORDER MATTERS HERE -- SOME MODULES ARE DEPENDANT ON OTHERS
from exceptions import FSQError, FSQInternalError, FSQEnvError,\
                       FSQEncodeError, FSQTimeFmtError,\
                       FSQMalformedEntryError, FSQCoerceError,\
                       FSQEnqueueError, FSQEnqueueMaxTriesError,\
                       FSQConfigError, FSQPathError, FSQInstallError,\
                       FSQCannotLockError, FSQWorkItemError,\
                       FSQTTLExpiredError, FSQMaxTriesError, FSQScanError,\
                       FSQDownError, FSQFailError
# constants relies on: exceptions, internal
from constants import FSQ_DELIMITER, FSQ_ENCODE, FSQ_TIMEFMT, FSQ_QUEUE,\
                      FSQ_DONE, FSQ_FAIL, FSQ_TMP, FSQ_DOWN, FSQ_ROOT,\
                      FSQ_ITEM_USER, FSQ_ITEM_GROUP, FSQ_ITEM_MODE,\
                      FSQ_QUEUE_USER, FSQ_QUEUE_GROUP, FSQ_QUEUE_MODE,\
                      FSQ_LOCK, FSQ_ENQUEUE_MAX_TRIES, FSQ_FAIL_TMP,\
                      FSQ_FAIL_PERM, FSQ_SUCCESS, FSQ_UNINSTALL_WAIT,\
                      FSQ_MAX_TRIES, FSQ_TTL

# path relies on: exceptions, constants, internal
import path

# configure relies on: exceptions, path, constants, internal
from configure import down, up, is_down

# install relies on exceptions, path, constants, configure, internal
from install import install, uninstall

# encode relies on: constants, exceptions, internal
from encode import encode, decode

# construct relies on: constants, exceptions, encode, internal
from construct import construct, deconstruct

# mkitem relies on: constants, exceptions, construct
from mkitem import mkitem

# enqueue module relies on: constants, exceptions, path, internal, mkitem
from enqueue import enqueue, senqueue, venqueue, vsenqueue

# done module relies on: constants, exceptions, path, internal, mkitem
from done import done, success, fail, fail_tmp, fail_perm

# items module relies on: exceptions, constants, path, construct, internal
from items import FSQWorkItem

# scan module relies on: exceptions, constants, path, items, configure, internal
from scan import FSQScanGenerator, scan

__all__ = [ 'FSQ_DELIMITER', 'FSQ_ENCODE', 'FSQ_TIMEFMT', 'FSQ_QUEUE',
            'FSQ_DONE', 'FSQ_FAIL', 'FSQ_TMP', 'FSQ_DOWN', 'FSQ_ROOT',
            'FSQ_ITEM_USER', 'FSQ_ITEM_GROUP', 'FSQ_QUEUE_USER',
            'FSQ_QUEUE_GROUP', 'FSQ_ITEM_MODE', 'FSQ_QUEUE_MODE', 'FSQ_LOCK',
            'FSQ_ENQUEUE_TRIES', 'FSQ_UNINSTALL_WAIT', 'FSQ_MAX_TRIES',
            'FSQ_TTL', 'path', 'down', 'up', 'is_down', 'install',
            'uninstall', 'encode', 'decode', 'construct', 'deconstruct',
            'enqueue', 'senqueue', 'venqueue', 'vsenqueue', 'FSQError',
            'FSQInternalError', 'FSQEnvError', 'FSQEncodeError',
            'FSQTimeFmtError', 'FSQMalformedEntryError', 'FSQCoerceError',
            'FSQEnqueueError', 'FSQEnqueueMaxTriesError', 'FSQConfigError',
            'FSQCannotLock', 'FSQWorkItemError', 'FSQTTLExpiredError',
            'FSQMaxTriesError', 'FSQScanError', 'FSQDownError', 'FSQFailError',
            'FSQWorkItem', 'FSQScanGenerator', 'scan' ]
