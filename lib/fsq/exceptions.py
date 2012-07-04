# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
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

class FSQInternalError(FSQError):
    '''Internal error for internal package use, if this is raised to caller
       something inside the package is not excpeting properly.'''
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

class FSQMaxEnqueueTriesError(FSQEnqueueError):
    '''Max attempts to enqueue exhausted'''
    pass
