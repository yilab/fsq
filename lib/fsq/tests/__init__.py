import os
import unittest
import pwd
import grp
import shutil
import errno

from .. import constants as _c
TEST_DIR = os.path.join(os.path.dirname(__file__), 'test_queues')
ROOT1 = os.path.join(TEST_DIR, 'queue')
ROOT2 = os.path.join(TEST_DIR, 'queue2')
NON_ASCII = u'\xf8'
TEST_QUEUE = 'test_{0}'
NORMAL = ( _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE, _c.FSQ_FAIL, _c.FSQ_DOWN,
            _c.FSQ_TRIGGER, )
NOT_NORMAL = ( 'foo', 'bar', 'baz', 'bang', 'wham', )
ILLEGAL_NAMES = ('..', '.', 'foo/bar',)
MODES = (00700, 02700, )
ILLEGAL_MODE = 'abcdefg'
ILLEGAL_NAME = {}
ILLEGAL_UID = -2
ILLEGAL_UNAME = tuple()
UID, GID = ( os.getuid(), os.getgid(), )
UNAME, GNAME = ( pwd.getpwuid(UID).pw_name, grp.getgrgid(GID).gr_name, )
ORIG_ROOT = _c.FSQ_ROOT
ORIG_MODES = ( _c.FSQ_QUEUE_MODE, _c.FSQ_ITEM_MODE, )
ORIG_QUEUE_UG = ( _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP, )
ORIG_ITEM_UG = ( _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP, )
NOROOT = os.path.join(TEST_DIR, 'noroot')
COUNT = 0

class FSQTestCase(unittest.TestCase):
    def setUp(self):
        COUNT = 0
        try:
            shutil.rmtree(TEST_DIR)
        except (OSError, IOError, ), e:
            if e.errno != errno.ENOENT:
                raise e
        os.mkdir(TEST_DIR, 00750)
        os.mkdir(ROOT1, 00750)
        os.mkdir(ROOT2, 00750)
        _c.FSQ_ROOT = ROOT1
        normalize()

    def tearDown(self):
        _c.FSQ_ROOT = ORIG_ROOT
        try:
            shutil.rmtree(TEST_DIR)
        except(OSError, IOError, ), e:
            if e.errno != errno.ENOENT:
                raise e
        normalize()

def normalize():
    global COUNT, _c
    _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE, _c.FSQ_FAIL,\
                           _c.FSQ_DOWN, _c.FSQ_TRIGGER = NORMAL
    _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP = ORIG_QUEUE_UG
    _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP = ORIG_ITEM_UG
    _c.FSQ_QUEUE_MODE, _c.FSQ_ITEM_MODE = ORIG_MODES
    COUNT += 1
    return TEST_QUEUE.format(COUNT)

def test_type_own_mode(st, t_path, f_type, uid, gid, mode):
    mask = 0
    # mask for directories (man 2 stat)
    if f_type == 'd':
        f_type = 'directory'
        mask = 0040000
    # mask for file (man 2 stat)
    if f_type == 'f':
        f_type = 'file'
        mask = 0100000
    # mask for FIFO (man 2 stat)
    elif f_type == 'p':
        f_type = 'FIFO'
        mask = 0010000
    if not st.st_mode&mask:
        raise ValueError(u'Not a {0}: {1}'.format(f_type, t_path))
    # st_mode&07777 -- mask out all non perms (man 2 stat)
    elif (uid is not None and st.st_uid != uid) or\
           (gid is not None and st.st_gid != gid) or\
           (mode is not None and (st.st_mode&07777) != mode):
        raise ValueError(u'incorrect uid|gid: {0}|{1} or mode {2}, expected'\
                         u' {3}|{4} with mode {5} for {6}'.format(st.st_uid,
                         st.st_gid, st.st_mode&07777, uid, gid, mode,
                         os.path.join(t_path)))

from .install import TestInstallUninstall
from .configure import TestUpDownIsDown

_LOADER = unittest.TestLoader()
_RUNNER = unittest.TextTestRunner(verbosity=2)
def run_install():
    install_tests = _LOADER.loadTestsFromTestCase(TestInstallUninstall)
    _RUNNER.run(install_tests)

def run_updownisdown():
    updownisdown_tests = _LOADER.loadTestsFromTestCase(TestUpDownIsDown)
    _RUNNER.run(updownisdown_tests)

def run_all():
    run_install()
    run_updownisdown()

__all__ = [ 'ROOT1', 'ROOT2', 'TEST_DIR', 'NON_ASCII', 'TEST_QUEUE',
            'NORMAL', 'WEIRDNESS', 'RAISES', 'ORIG_ROOT', 'ORIG_MODES',
            'ORIG_QUEUE_UG', 'ORIG_ITEM_UG', 'MODES', 'UID', 'GID', 'UNAME',
            'GNAME', 'NOROOT', 'TestInstallUninstall', 'test_type_own_mode',
            'FSQTestCase' ]
