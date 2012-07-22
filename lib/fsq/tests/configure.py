import os
import errno
from . import ROOT1, ROOT2, NON_ASCII, TEST_QUEUE, NORMAL, NOT_NORMAL,\
              ILLEGAL_NAMES, ILLEGAL_MODE, ILLEGAL_NAME, ORIG_MODES,\
              ORIG_QUEUE_UG, ORIG_ITEM_UG, MODES, UID, GID, UNAME, GNAME,\
              NOROOT, ILLEGAL_UID, ILLEGAL_UNAME, test_type_own_mode,\
              FSQTestCase, normalize
from .. import install, down, up, is_down, constants as _c, FSQPathError,\
               FSQInstallError, FSQCoerceError, FSQConfigError

def _valid_up(queue):
    d_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_DOWN)
    try:
        os.stat(d_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise e
        return True
    raise ValueError('queue is down, should be up: {0}'.format(queue))

def _valid_down(queue, user=None, group=None, mode=None):
    d_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_DOWN)
    st = os.stat(d_path)
    test_type_own_mode(st, d_path, 'f', user if user is None else UID,
                       group if group is None else GID, mode)
    return True

class TestUpDownIsDown(FSQTestCase):
    def _cycle(self, queue=None, **kwargs):
        queue = self._down(queue, **kwargs)
        self.assertTrue(is_down(queue))
        self._up(queue)
        self.assertFalse(is_down(queue))
        return queue

    def _down(self, queue=None, installqueue=True, is_down=False,
              fsq_down=None, **kwargs):
        if queue is None:
            queue = normalize()
        if fsq_down is not None:
            _c.FSQ_DOWN = fsq_down
        if installqueue == True:
            install(queue, is_down)
        down(queue, **kwargs)
        self.assertTrue(_valid_down(queue, **kwargs))
        return queue

    def _up(self, queue):
        up(queue)
        self.assertTrue(_valid_up(queue))

    def test_basic(self):
        '''Test all permutations of arguments, or most of them anyway,
           combined with permutations of module constants values.'''
        for root in ROOT1, ROOT2:
            # test different down file names
            for d in (_c.FSQ_DOWN, NOT_NORMAL[4], NON_ASCII,):
                for is_d in True, False:
                    # test normal cycle with a set down
                    queue = self._cycle(fsq_down=d, is_down=is_d)
                    # test that up doesn't throw an error if already up
                    up(queue)

                    # test with user id/group id and user name/group name
                    for uid, gid in ((UID, GID,), (UNAME, GNAME,)):
                        # just user kwarg
                        self._cycle(fsq_down=d, is_down=is_d, user=uid)
                        # just group kwarg
                        self._cycle(fsq_down=d, is_down=is_d, group=gid)
                        # both
                        self._cycle(fsq_down=d, is_down=is_d, user=uid,
                                    group=gid)
                        for mode in MODES:
                            # just mode kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode)
                            # mode and user kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        user=uid)
                            # mode and group kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        group=gid)
                            # mode and group and user kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        user=uid, group=gid)

    def test_invalrootorqueue(self):
        '''Test proper failure for non-existant roots and non-existant
           queues'''
        # test invalid root or no queue
        for root in (NOROOT, ROOT1,):
            _c.FSQ_ROOT = root
            for fn in (down, up, is_down,):
                self.assertRaises(FSQConfigError, fn, 'abc')

    def test_permdenied(self):
        '''Test proper failure for permission denied'''
        # test permission denied root
        queue = self._cycle()
        os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0)
        for fn in (down, up, is_down, ):
            self.assertRaises(FSQConfigError, fn, queue)
        os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0750)

    def test_invalnames(self):
        '''Test failure with invalid or illegal names'''
        for root in (ROOT1, ROOT2,):
            _c.FSQ_ROOT = root
            for name in ILLEGAL_NAMES:
                queue = self._cycle()
                _c.FSQ_DOWN = name
                for fn in (down, up, is_down,):
                    self.assertRaises(FSQPathError, fn, queue)

            queue = self._cycle()
            _c.FSQ_DOWN = ILLEGAL_NAME
            for fn in (down, up, is_down,):
                self.assertRaises(FSQCoerceError, fn, queue)
