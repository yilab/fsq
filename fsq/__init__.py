# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/__init__.py -- wraps fsq in a bow.
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.

# ORDER MATTERS HERE -- SOME MODULES ARE DEPENDANT ON OTHERS
from exceptions import FSQError, FSQEnvError, FSQEncodeError,\
                       FSQTimeFmtError, FSQMalformedEntryError,\
                       FSQCoerceError, FSQEnqueueError, FSQConfigError,\
                       FSQPathError, FSQInstallError, FSQCannotLockError,\
                       FSQWorkItemError, FSQTTLExpiredError,\
                       FSQMaxTriesError, FSQScanError, FSQDownError,\
                       FSQDoneError, FSQFailError, FSQTriggerPullError,\
                       FSQHostsError, FSQReenqueueError, FSQPushError

# constants relies on: exceptions, internal
import constants

# const relies on: constants, exceptions, internal
from const import const, set_const # has tests

# path relies on: exceptions, constants, internal
import path # has tests

# configure relies on: exceptions, path, constants, internal, hosts
from configure import down, up, is_down, trigger, untrigger, trigger_pull,\
                      down_host, up_host, host_is_down, host_trigger,\
                      host_untrigger, host_trigger_pull, hosts # has tests

# install relies on exceptions, path, constants, configure, internal, hosts
from install import install, uninstall, install_host, uninstall_host # has tests

# encode relies on: constants, exceptions, internal
from encode import encode, decode # has tests

# construct relies on: constants, exceptions, encode, internal
from construct import construct, deconstruct # has tests

# enqueue relies on: constants, exceptions, path, internal, mkitem
from enqueue import enqueue, senqueue, venqueue, vsenqueue, reenqueue,\
                    sreenqueue, vreenqueue, vsreenqueue

# done relies on: constants, exceptions, path, internal, mkitem
from done import done, success, fail, fail_tmp, fail_perm

# items relies on: exceptions, constants, path, construct, internal
from items import FSQWorkItem

# scan relies on: exceptions, constants, path, items, configure, internal
from scan import FSQScanGenerator, scan

# remote.v1 relies on: enqueue
import remote

# push relies on: exceptions, constants and items
from push import push

__all__ = [ 'FSQError', 'FSQEnvError', 'FSQEncodeError', 'FSQTimeFmtError',
            'FSQMalformedEntryError', 'FSQCoerceError', 'FSQEnqueueError',
            'FSQConfigError', 'FSQCannotLock', 'FSQWorkItemError',
            'FSQTTLExpiredError', 'FSQMaxTriesError', 'FSQScanError',
            'FSQDownError', 'FSQDoneError', 'FSQFailError', 'FSQInstallError',
            'FSQTriggerPullError', 'FSQCannotLockError', 'FSQPathError',
            'path', 'constants', 'const', 'set_const', 'down', 'up',
            'is_down', 'trigger', 'untrigger', 'trigger_pull', 'install',
            'uninstall', 'encode', 'decode', 'construct', 'deconstruct',
            'enqueue', 'senqueue', 'venqueue', 'vsenqueue', 'success', 'fail',
            'done', 'fail_tmp', 'fail_perm', 'FSQWorkItem',
            'FSQScanGenerator', 'scan', 'install_host', 'FSQHostsError',
            'hosts', 'down_host', 'up_host', 'host_is_down', 'host_trigger',
            'host_untrigger', 'host_trigger_pull', 'host_root',
            'uninstall_host', 'FSQReenqueueError', 'reenqueue', 'sreenqueue',
            'vreenqueue', 'vsreenqueue', 'remote', 'FSQPushError', 'push', ]
