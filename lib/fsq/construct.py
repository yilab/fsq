# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/construct.py -- provides name construction functions: construct,
#                     deconstruct, escape, descape
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import errno
import os

from . import FSQEscapeError, FSQMalformedEntryError, FSQ_DELIMITER,\
              FSQ_ESCAPE
from .internal import coerce_unicode

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
_ESCAPED = (os.path.sep,)

####### EXPOSED METHODS #######
def construct(args, delimiter=FSQ_DELIMITER, escapeseq=FSQ_ESCAPE):
    '''Construct a queue-name from a set of arguments and a delimiter'''
    # make everything unicode
    name = sep = u''
    delimiter = coerce_unicode(delimiter)
    escapeseq = coerce_unicode(escapeseq)
    for arg in args:
        name = delimiter.join([name, escape(coerce_unicode(arg),
                              escapeseq=escapeseq, delimiter=delimiter)])

    return name

def deconstruct(name, escapeseq=FSQ_ESCAPE):
    '''Deconstruct a queue-name to a set of arguments'''
    name = coerce_unicode(name)
    escapeseq = coerce_unicode(escapeseq)
    new_arg = sep = u''
    args = []
    if len(delimiter) > 1:
        raise FSQMalformedEntryError(errno.EINVAL, u'cannot derive delimiter'\
                                     u'from: {0}'.format(name))
    # edge case, no args
    elif len(name) == 1:
        return args

    delimiter = name[0]
    escaped = False
    # normal case
    for c in name[1:]:
        if escaped:
            escaped = False
        elif c == escapeseq:
            escaped = True
        elif c == delimiter:
            # at delimiter, append and reset working arg
            args.append(descape(new_arg, delimiter=delimiter,
                                escapeseq=escapeseq))
            new_arg = ''
            continue

        new_arg = sep.join([new_arg, c])

    # append our last arg
    args.append(descape(new_arg, delimiter=delimiter,
                        escapeseq=escapeseq))
    return args


def escape(arg, delimiter=FSQ_DELIMITER, escapeseq=FSQ_ESCAPE):
    '''Escape a single argument for the file-system'''
    arg = coerce_unicode(arg)
    new_arg = sep = u''
    delimiter = coerce_unicode(delimiter)
    escapeseq = coerce_unicode(escapeseq)

    if len(escapeseq) != 1:
        raise FSQEscapeError(errno.EINVAL, u'escape sequence must be 1'\
                             u' character, not {0}'.format(len(escapeseq)))

    # char-wise escape walk
    for seq in arg:
        if seq == delimiter or seq == escapeseq or seq in _ESCAPED:
            seq = sep.join([escapeseq, seq])
        new_arg = sep.join([new_arg, seq])

    return new_arg

def descape(arg, delimiter=FSQ_DELIMITER, escapeseq=FSQ_ESCAPE):
    '''Descape a single argument from the file-system'''
    arg = coerce_unicode(arg)
    new_arg = sep = u''
    delimiter = coerce_unicode(delimiter)
    escapeseq = coerce_unicode(escapeseq)

    if len(escapeseq) != 1:
        raise FSQEscapeError(errno.EINVAL, u'escape sequence must be 1'\
                             u'character, not {0}'.format(len(escapeseq)))

    # char-wise descape walk -- minimally stateful
    escaped = False
    for c in arg:
        if escaped:
            escaped = False
        elif c == escapeseq:
            escaped = True
            continue
        new_arg = sep.join([new_arg, c])

    return new_arg
