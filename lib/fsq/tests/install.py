import os
import pwd
import grp
import unittest
import shutil
import errno

from . import ROOT1, ROOT2, TEST_DIR, NON_ASCII, TEST_QUEUE, NORMAL,\
              NOT_NORMAL, ILLEGAL_NAMES, ILLEGAL_MODE, ILLEGAL_NAME,\
              ORIG_ROOT, ORIG_MODES, ORIG_QUEUE_UG, ORIG_ITEM_UG, MODES, UID,\
              GID, UNAME, GNAME, NOROOT, ILLEGAL_UID, ILLEGAL_UNAME
from .. import install, uninstall, constants as _c, FSQPathError,\
               FSQInstallError, FSQCoerceError, FSQConfigError

_COUNT = 0

def _test_type_own_mode(st, t_path, f_type, uid, gid, mode):
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
                         st.st_gid, st.st_mode, uid, gid, mode,
                         os.path.join(_c.FSQ_ROOT, queue, d)))

def _valid_uninstall(queue):
    dirs = os.listdir(_c.FSQ_ROOT)
    for d in dirs:
        if d == queue:
            return False
    return True

def _valid_install(queue, is_down=None, is_triggered=None, user=None,
                   group=None, mode=None, item_user=None, item_group=None,
                   item_mode=None):
    dirs = os.listdir(os.path.join(_c.FSQ_ROOT, queue))
    seen = []
    allowed = set([ _c.FSQ_FAIL, _c.FSQ_TMP, _c.FSQ_DONE, _c.FSQ_QUEUE, ])
    if is_down:
        allowed = allowed|set([ _c.FSQ_DOWN, ])
    if is_triggered:
        allowed = allowed|set([ _c.FSQ_TRIGGER, ])
    for d in dirs:
        d = unicode(d, encoding='utf8')
        if d in allowed:
            seen.append(d)
            t_path = os.path.join(_c.FSQ_ROOT, queue, d)
            st = os.stat(t_path)
            # tests for directory install
            if d not in ( _c.FSQ_DOWN, _c.FSQ_TRIGGER ):
                _test_type_own_mode(st, t_path, 'd',
                                    user if user is None else UID,
                                    group if group is None else GID, mode)
            else:
                f_type = 'f'
                # is it a FIFO (man 2 stat)
                if d == _c.FSQ_TRIGGER:
                    f_type = 'p'
                _test_type_own_mode(st, t_path, f_type,
                    item_user if item_user is None else UID,
                    item_group if item_group is None else GID, item_mode)
        else:
            raise ValueError('illegal entry: {0}; install failed'.format(d))
    if len(set(seen)^allowed):
        raise ValueError('missing entries: {0}; install'\
                         ' failed'.format(set(seen)^allowed))
    return True

def _normalize():
    global _COUNT, _c
    _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE, _c.FSQ_FAIL,\
                           _c.FSQ_DOWN, _c.FSQ_TRIGGER = NORMAL
    _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP = ORIG_QUEUE_UG
    _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP = ORIG_ITEM_UG
    _c.FSQ_QUEUE_MODE, _c.FSQ_ITEM_MODE = ORIG_MODES
    _COUNT += 1
    return TEST_QUEUE.format(_COUNT)

class TestInstallUninstall(unittest.TestCase):
    def setUp(self):
        try:
            shutil.rmtree(TEST_DIR)
        except (OSError, IOError, ), e:
            if e.errno != errno.ENOENT:
                raise e
        os.mkdir(TEST_DIR, 00750)
        os.mkdir(ROOT1, 00750)
        os.mkdir(ROOT2, 00750)

    def tearDown(self):
        _c.FSQ_ROOT = ORIG_ROOT
        try:
            shutil.rmtree(TEST_DIR)
        except(OSError, IOError, ), e:
            if e.errno != errno.ENOENT:
                raise e

    def _install(self, queue=None, **kwargs):
        if queue is None:
            queue = _normalize()
        install(queue, **kwargs)
        self.assertTrue(_valid_install(queue, **kwargs))
        return queue

    def _uninstall(self, queue, **kwargs):
        uninstall(queue, **kwargs)
        self.assertTrue(_valid_uninstall(queue))

    def test_basic(self):
        '''Test all permutations of arguments, or most of them anyway,
           combined with permuatations of module constants values.'''
        for root in ROOT1, ROOT2:
            _c.FSQ_ROOT = root
            # kwargsless install to root
            queue = self._install()
            self._uninstall(queue)

            for down in True, False:
                # no is_triggered kwarg
                queue = self._install(is_down=down)
                self._uninstall(queue)

                for is_t in True, False:
                    # no down kwarg
                    queue = self._install(is_triggered=is_t)
                    self._uninstall(queue)

                    # standard install -- all kwargs
                    queue = self._install(is_down=down, is_triggered=is_t)
                    self._uninstall(queue)

                    # change things up
                    queue = _normalize()
                    _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE,\
                                 _c.FSQ_FAIL, _c.FSQ_DOWN = NOT_NORMAL
                    self._install(queue, is_down=down, is_triggered=is_t)
                    self._uninstall(queue)

                    # test unicodeness
                    queue = _normalize()
                    _c.FSQ_TMP = NON_ASCII
                    self._install(queue, is_down=down, is_triggered=is_t)
                    self._uninstall(queue)
                # END is_triggered LOOP
            # END down LOOP
        # END ROOT loop

    def test_collide(self):
        '''Test installing to an already installed path.'''
        for root in ROOT1, ROOT2:
            _c.FSQ_ROOT = root
            queue = self._install()
            self.assertRaises(FSQInstallError, install, queue)
            self._uninstall(queue)

    def test_invalroot(self):
        '''Test install/uninstall to/from a non-existant FSQ_ROOT'''
        queue = _normalize()
        _c.FSQ_ROOT = NOROOT
        self.assertRaises(FSQInstallError, install, queue)
        self.assertRaises(FSQInstallError, uninstall, queue)


    def test_invalnames(self):
        '''Test installing with illegal names'''
        for root in ROOT1, ROOT2:
            _c.FSQ_ROOT = root
            # verify installing queue with non-coercable name fails
            _normalize()
            self.assertRaises(FSQCoerceError, install, ILLEGAL_NAME)
            self.assertRaises((OSError, AttributeError,), _valid_install,
                              ILLEGAL_NAME)
            for name in ILLEGAL_NAMES:
                _normalize()
                self.assertRaises(FSQPathError, install, name)
                # verify that the queue doesn't exist
                self.assertRaises((OSError,ValueError,), _valid_install, name)
                for other in ('FSQ_QUEUE', 'FSQ_TMP', 'FSQ_FAIL', 'FSQ_DOWN',
                              'FSQ_TRIGGER'):
                    queue = _normalize()
                    setattr(_c, other, name)
                    # verify path error
                    self.assertRaises(FSQPathError, install, queue,
                                      is_down=True, is_triggered=True)
                    # verify not installed
                    self.assertRaises(OSError, _valid_install, queue,
                                      is_down=True, is_triggered=True)

                    # verify non-string CoerceErrors
                    queue = _normalize()
                    setattr(_c, other, ILLEGAL_NAME)
                    self.assertRaises(FSQCoerceError, install, queue,
                                      is_down=True, is_triggered=True)
                    self.assertRaises((OSError, ValueError,), _valid_install,
                                      queue, is_down=True, is_triggered=True)

    def test_usergroup(self):
        '''Test installing with queue user|group for tmp/done/fail/queue'''
        for uid, gid in ((UID, GID, ), (UNAME, GNAME, )):
            for root in ROOT1, ROOT2:
                _c.FSQ_ROOT = root
                # test only user kwarg
                queue = self._install(user=uid)
                self._uninstall(queue)

                # test only group kwarg
                queue = self._install(group=gid)
                self._uninstall(queue)

                # test with uid/gid passed in
                queue = self._install(user=uid, group=gid)
                self._uninstall(queue)

                # test with uid/gid set
                queue = _normalize()
                _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP = ( uid, gid, )
                self._install(queue)
                self._uninstall(queue)

                # plays well with other flags?
                for down in True, False:
                    for is_t in True, False:
                        queue = self._install(user=uid, group=gid,
                                              is_down=down, is_triggered=is_t)
                        self._uninstall(queue)
                    #END is_triggered LOOP
                # END down LOOP
            # END root LOOP
            queue = _normalize()
            uid = gid = ILLEGAL_UID
            self.assertRaises(FSQInstallError, install, queue, user=uid)
            self.assertRaises(OSError, _valid_install, queue, user=uid)
            self.assertRaises(FSQInstallError, install, queue, group=gid)
            self.assertRaises(OSError, _valid_install, queue, group=gid)
            self.assertRaises(FSQInstallError, install, queue, user=uid,
                              group=gid)
            self.assertRaises(OSError, _valid_install, queue, user=uid,
                              group=gid)
            queue = _normalize()
            uid = gid = ILLEGAL_UNAME
            self.assertRaises(TypeError, install, queue, user=uid)
            self.assertRaises((OSError, AttributeError,), _valid_install,
                              queue, user=uid)
            self.assertRaises(TypeError, install, queue, group=gid)
            self.assertRaises((OSError, AttributeError,), _valid_install,
                              queue, group=gid)
            self.assertRaises(TypeError, install, queue, user=uid,
                              group=gid)
            self.assertRaises((OSError, AttributeError,), _valid_install,
                              queue, user=uid, group=gid)
        # END uid,gid loop

    def test_itemusergroup(self):
        '''Test installing with item user|group for down/trigger-s'''
        for uid, gid in ((UID, GID, ), (UNAME, GNAME, )):
            for root in ROOT1, ROOT2:
                _c.FSQ_ROOT = root
                # test only user kwarg
                queue = self._install(item_user=uid)
                self._uninstall(queue, item_user=uid)

                # test only group kwarg
                queue = self._install(item_group=gid)
                self._uninstall(queue, item_group=gid)

                # test with uid/gid passed in
                queue = self._install(item_user=uid, item_group=gid)
                self._uninstall(queue, item_user=uid, item_group=gid)

                # test with uid/gid set
                queue = _normalize()
                _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP = ( uid, gid, )
                self._install(queue)
                self._uninstall(queue)

                # plays well with other flags?
                for down in True, False:
                    for is_t in True, False:
                        for quid, qgid in ((UID, GID,), (UNAME, GNAME,)):
                            queue = self._install(item_user=uid,
                                                  item_group=gid,
                                                  is_down=down,
                                                  is_triggered=is_t,
                                                  user=quid, group=qgid)
                            self._uninstall(queue, item_user=uid,
                                            item_group=gid)
                        # END queue uid/gid LOOP
                    # END is_triggered LOOP
                # END down LOOP
            # END root LOOP
            for uid, gid in ((ILLEGAL_UID, ILLEGAL_UID,),
                            (ILLEGAL_UNAME, ILLEGAL_UNAME,)):
                queue = _normalize()
                uid = gid = ILLEGAL_UID
                self.assertRaises(FSQConfigError, install, queue,
                                  item_user=uid, is_down=True)
                self.assertRaises((OSError, AttributeError,), _valid_install,
                                  queue, item_user=uid, is_down=True)
                self.assertRaises(FSQConfigError, install, queue,
                                  item_group=gid, is_down=True)
                self.assertRaises((OSError, AttributeError,),  _valid_install,
                                  queue, item_group=gid, is_down=True)
                self.assertRaises(FSQConfigError, install, queue,
                                  item_user=uid, item_group=gid, is_down=True)
                self.assertRaises((OSError, AttributeError,), _valid_install,
                                  queue, item_user=uid, item_group=gid,
                                  is_down=True)

                # verify install with illegal works, and uninstall fails
                queue = self._install(item_user=uid)
                self.assertRaises(FSQConfigError, uninstall, queue,
                                  item_user=uid)
                self.assertFalse(os.path.exists(os.path.join(root, queue,
                                 _c.FSQ_DOWN)))
                queue = self._install(item_group=gid)
                self.assertRaises(FSQConfigError, uninstall, queue,
                                  item_group=gid)
                self.assertFalse(os.path.exists(os.path.join(root, queue,
                                 _c.FSQ_DOWN)))
                queue = self._install(item_user=uid, item_group=gid)
                self.assertRaises(FSQConfigError, uninstall, queue,
                                  item_user=uid, item_group=gid)
                self.assertFalse(os.path.exists(os.path.join(root, queue,
                                 _c.FSQ_DOWN)))
            # END ILLEGAL LOOP
        # END uid,gid loop

    def test_mode(self):
        '''Test installing with queue modes for tmp/done/fail/queue'''
        for mode in MODES:
            for root in ROOT1, ROOT2:
                _c.FSQ_ROOT = root
                # test only mode kwarg
                queue = self._install(mode=mode)
                self._uninstall(queue)

                # test with mode set
                queue = _normalize()
                _c.FSQ_QUEUE_MODE = mode
                self._install(queue)
                self._uninstall(queue)

                # plays well with other flags?
                for down in True, False:
                    for is_t in True, False:
                        for uid, gid in ((UID, GID,), (UNAME, GNAME,)):
                            for quid, qgid in ((UID, GID,), (UNAME, GNAME,)):
                                queue = self._install(mode=mode, is_down=down,
                                                      is_triggered=is_t,
                                                      user=quid, group=qgid,
                                                      item_user=uid,
                                                      item_group=gid)
                                self._uninstall(queue, item_user=uid,
                                                item_group=gid)
                            # END queue uid/gid LOOP
                        # END uid,gid loop
                    # END is_triggered LOOP
                # END down LOOP
            # END root LOOP
        # END mode LOOP

    def test_itemmode(self):
        '''Test installing with item modes for down/trigger-s'''
        for mode in MODES:
            for root in ROOT1, ROOT2:
                _c.FSQ_ROOT = root
                # test only mode kwarg
                queue = self._install(item_mode=mode)
                self._uninstall(queue, item_mode=mode)

                # test with mode set
                queue = _normalize()
                _c.FSQ_ITEM_MODE = mode
                self._install(queue)
                self._uninstall(queue)

                # plays well with other flags?
                for down in True, False:
                    for is_t in True, False:
                        for uid, gid in ((UID, GID,), (UNAME, GNAME,)):
                            for quid, qgid in ((UID, GID,), (UNAME, GNAME,)):
                                for qm in MODES:
                                    queue = self._install(item_mode=mode,
                                                          mode=qm,
                                                          is_down=down,
                                                          is_triggered=is_t,
                                                          user=quid,
                                                          group=qgid,
                                                          item_user=uid,
                                                          item_group=gid)
                                    self._uninstall(queue, item_user=uid,
                                                    item_group=gid,
                                                    item_mode=mode)
                            # END queue uid/gid LOOP
                        # END uid,gid loop
                    # END is_triggered LOOP
                # END down LOOP
            # END root LOOP
        # END mode LOOP
