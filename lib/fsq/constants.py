# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/constants.py -- a place for constants.  per FSQ specification,
#   constants take their value from the calling program environment
#   (if available), and default to the the expected values.
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
#   NB: changes to environment following first import, will not
#       affect values potentially a bug to clean up later.
#
# This software is for POSIX compliant systems only.
import os
from . import FSQEnvError
from .internal import coerce_unicode

# CONSTANTS WHICH ARE AFFECTED BY ENVIRONMENT
FSQ_DELIMITER = coerce_unicode(os.environ.get("FSQ_DELIMITER", u'_'))
FSQ_ESCAPE = coerce_unicode(os.environ.get("FSQ_ESCAPE", u'\\'))
FSQ_TIMEFMT = coerce_unicode(os.environ.get("FSQ_TIMEFMT", u'%Y%m%d%H%M%S'))
FSQ_QUEUE = coerce_unicode(os.environ.get("FSQ_QUEUE", u'queue'))
FSQ_DONE = coerce_unicode(os.environ.get("FSQ_DONE", u'done'))
FSQ_FAIL = coerce_unicode(os.environ.get("FSQ_FAIL", u'fail'))
FSQ_TMP = coerce_unicode(os.environ.get("FSQ_TMP", u'tmp'))
FSQ_DOWN = coerce_unicode(os.environ.get("FSQ_DOWN", u'down'))
FSQ_ROOT = coerce_unicode(os.environ.get("FSQ_ROOT", u''))

try:
    # failure cases
    FSQ_FAIL_TMP = int(os.environ.get("FSQ_FAIL_TMP", 111))
    FSQ_FAIL_PERM = int(os.environ.get("FSQ_FAIL_PERM", 100))
    # success
    FSQ_DONE = int(os.environ.get("FSQ_DONE", 0))
except ValueError, e:
    raise FSQEnvError(errno.EINVAL, e.message)
