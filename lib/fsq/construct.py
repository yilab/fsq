# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/construct.py -- provides name construction functions: construct,
#                     deconstruct, encode, decode
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import errno

from . import FSQMalformedEntryError, FSQ_DELIMITER, FSQ_ENCODE, encode,\
              decode
from .internal import coerce_unicode

####### EXPOSED METHODS #######
def construct(args, delimiter=FSQ_DELIMITER, encodeseq=FSQ_ENCODE):
    '''Construct a queue-name from a set of arguments and a delimiter'''
    # make everything unicode
    name = sep = u''
    delimiter = coerce_unicode(delimiter)
    encodeseq = coerce_unicode(encodeseq)
    for arg in args:
        name = delimiter.join([name, escape(coerce_unicode(arg),
                              encodeseq=encodeseq, delimiter=delimiter)])

    return name

def deconstruct(name, encodeseq=FSQ_ENCODE):
    '''Deconstruct a queue-name to a set of arguments'''
    name = coerce_unicode(name)
    encodeseq = coerce_unicode(encodeseq)
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
        elif c == encodeseq:
            escaped = True
        elif c == delimiter:
            # at delimiter, append and reset working arg
            args.append(descape(new_arg, delimiter=delimiter,
                                encodeseq=encodeseq))
            new_arg = ''
            continue

        new_arg = sep.join([new_arg, c])

    # append our last arg
    args.append(descape(new_arg, delimiter=delimiter,
                        encodeseq=encodeseq))
    return args
