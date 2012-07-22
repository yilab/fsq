import os
import unittest
import pwd
import grp

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

from .install import TestInstallUninstall

def run_all():
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=2)

    install_tests = loader.loadTestsFromTestCase(TestInstallUninstall)
    runner.run(install_tests)

__all__ = [ 'ROOT1', 'ROOT2', 'TEST_DIR', 'NON_ASCII', 'TEST_QUEUE',
            'NORMAL', 'WEIRDNESS', 'RAISES', 'ORIG_ROOT', 'ORIG_MODES',
            'ORIG_QUEUE_UG', 'ORIG_ITEM_UG', 'MODES', 'UID', 'GID', 'UNAME',
            'GNAME', 'NOROOT', 'TestInstallUninstall' ]
