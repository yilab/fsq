# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
#
# fsq/exceptions.py -- provides exceptions for fsq, exceptions in their own
#                      module avoids circular imports
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.

class FSQError(OSError):
    '''root for FSQErrors, only used to except any FSQ error, never raised'''
    pass

class FSQEnvError(FSQError):
    '''An error if something cannot be loaded from env, or env has an invalid
       value'''
    pass

class FSQEncodeError(FSQError):
    '''An error occured while encoding or decoding an argument'''
    pass

class FSQEnqueueError(FSQError):
    '''An error occured while enqueuing an item'''

class FSQTimeFmtError(FSQError):
    '''Either time format is invalid, or time is not formatted correctly to
       the expected format'''
    pass

class FSQMalformedEntryError(FSQError):
    '''Queue entry is malformed and cannot be parsed'''
    pass

class FSQCoerceError(FSQError):
    '''Everything is coerced to unicode'''
    pass

class FSQConfigError(FSQError):
    '''Error configuring a queue'''
    pass

class FSQPathError(FSQError):
    '''Error constructing a path from componants'''
    pass

class FSQInstallError(FSQError):
    '''Error installing a queue'''
    pass

class FSQCannotLockError(FSQError):
    '''Error locking queue item'''
    pass

class FSQWorkItemError(FSQError):
    '''An Error while trying to work on an item'''

class FSQTTLExpiredError(FSQWorkItemError):
    '''TTL has expired, item has failed permanantly'''
    pass

class FSQMaxTriesError(FSQWorkItemError):
    '''Max Tries exhausted for a Work-Item, item has failed permanantly'''
    pass

class FSQScanError(FSQError):
    '''An error occured while trying to scan a queue'''
    pass

class FSQDownError(FSQScanError):
    '''Attempt to scan a down'ed queue'''
    pass

class FSQDoneError(FSQError):
    '''Attempt to done/succeed an item failed'''
    pass

class FSQFailError(FSQError):
    '''Attempt to fail an item failed'''
    pass

class FSQTriggerPullError(FSQError):
    '''Error pulling a trigger (writing a byte O_NONBLOCK to a fifo)'''
    pass
