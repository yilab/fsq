import os
import pwd
import grp

from .. import constants as _c

# Test Queue Directory
TEST_DIR = os.path.join(os.path.dirname(__file__), u'test_queues')

# The original (default) FSQ_ROOT value
ORIG_ROOT = _c.FSQ_ROOT

# 2 FSQ_ROOT directories for testing, within TEST_DIR
ROOT1 = os.path.join(TEST_DIR, u'queue')
ROOT2 = os.path.join(TEST_DIR, u'queue2')

# A Non-ASCII sequence for testing non-ascii installs
NON_ASCII = u'\xf8'

# FMT String for programmatic test queue creation
TEST_QUEUE = u'test_{0}'

# The Normal settings (e.g. original settings)
NORMAL = ( _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE, _c.FSQ_FAIL, _c.FSQ_DOWN,
            _c.FSQ_TRIGGER, )

# Overrides which should work always, for the ``Normal'' Settings
NOT_NORMAL = ( u'foo', u'bar', u'baz', u'bang', u'wham', )

# Names which are not allowed for queues, or directories within queues
ILLEGAL_NAMES = (u'..', u'.', u'foo/bar',)

# The original (default) FSQ queue and item modes
ORIG_MODES = ( _c.FSQ_QUEUE_MODE, _c.FSQ_ITEM_MODE, )

# Some valid modes to test with
MODES = (00700, 02700, )
STR_MODES = (u'00700', u'02700', )

# Some valid charsets
ORIG_CHARSET = _c.FSQ_CHARSET
CHARSETS = ('ascii', 'latin-1',)

# A mode that is always illegal, no matter what
ILLEGAL_MODE = u'abcdefg'

# An illegal user name (not a string)
ILLEGAL_NAME = {}

# An illegal UID for testing uid/gid (-1 sets to same, so we use -2)
ILLEGAL_UID = -2

# An illegal User name for testing user/group names
ILLEGAL_UNAME = tuple()

# The original (default) FSQ user/group values for queues
ORIG_QUEUE_UG = ( _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP, )
# The original (default) FSQ user/group values for items
ORIG_ITEM_UG = ( _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP, )

# our current UID/GID for testing explicit setting of uid/gid
UID, GID = ( os.getuid(), os.getgid(), )

# our current user/group name for testing explicit setting of user/group names
UNAME, GNAME = ( pwd.getpwuid(UID).pw_name, grp.getgrgid(GID).gr_name, )

# A root we'll assume will never exist
NOROOT = os.path.join(TEST_DIR, u'noroot')

# A constant we'll assume doesn't exist
NOCONST = u'FSR_BOOM'

# Count of queues installed during current test
COUNT = 0

# Overall Count of queues installed across all tests
TOTAL_COUNT = 0

# Different Encode Sequence Char
ENCODE = '^'
ILLEGAL_ENCODE = '^^'

# Different Delimiter Char
DELIMITER = '.'
ILLEGAL_DELIMITER = '..'

# Extra Chars to Encode
ENCODED = ('a', 'b', 'c',)

# Original Encode/Delimiter
ORIG_ENCODE_DELIMITER = ( _c.FSQ_ENCODE, _c.FSQ_DELIMITER, )

PAYLOAD = NORMAL[0]*100
NON_ASCII_PAYLOAD = NON_ASCII*1024
SOCKET = os.path.join(TEST_DIR, u'sock-s')
FIFO = os.path.join(TEST_DIR, u'fifo-s')
FILE = os.path.join(TEST_DIR, u'test-enqueue')
NON_ASCII_FILE = os.path.join(TEST_DIR, u'test-enqueue{0}'.format(NON_ASCII))
