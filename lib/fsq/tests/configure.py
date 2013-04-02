import os
import errno

from . import FSQTestCase
from .internal import test_type_own_mode, normalize
from .constants import ROOT1, ROOT2, NON_ASCII, NOT_NORMAL, ILLEGAL_NAMES,\
                       ILLEGAL_MODE, ILLEGAL_NAME, ILLEGAL_UID,\
                       ILLEGAL_UNAME, MODES, UID, GID, UNAME, GNAME, NOROOT
# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import install, down, up, is_down, trigger, untrigger, trigger_pull,\
               constants as _c, FSQPathError, FSQCoerceError, FSQConfigError,\
               FSQTriggerPullError

########## INTERNAL VALIDATION METHODS
def _valid_up(queue):
    '''Boolean Test if ``up'' Succeeded'''
    d_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_DOWN)
    try:
        os.stat(d_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise e
        return True
    raise ValueError('queue is down, should be up: {0}'.format(queue))

def _valid_down(queue, user=None, group=None, mode=None):
    '''Boolean Test if ``down'' Succeeded'''
    d_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_DOWN)
    st = os.stat(d_path)
    test_type_own_mode(st, d_path, 'f', user if user is None else UID,
                       group if group is None else GID, mode)
    return True

def _valid_trigger(queue, user=None, group=None, mode=None):
    '''Boolean Test if ``trigger'' Succeeded'''
    t_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_TRIGGER)
    st = os.stat(t_path)
    test_type_own_mode(st, t_path, 'p', user if user is None else UID,
                       group if group is None else GID, mode)
    return True

def _valid_untrigger(queue):
    '''Boolean Test if ``untrigger'' Succeeded'''
    t_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_TRIGGER)
    try:
        os.stat(t_path)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise e
        return True
    raise ValueError('queue is triggered, should be untriggered:'\
                     ' {0}'.format(queue))

########### EXPOSED TEST CASES
class TestUpDownIsDown(FSQTestCase):
    '''Test the down, up and is_down functions provided by the configure
       module of fsq.'''
    _fns = ( down, up, is_down, )
    _perm = FSQConfigError
    _var = 'FSQ_DOWN'
    def _cycle(self, queue=None, **kwargs):
        queue = self._down(queue, **kwargs)
        self.assertTrue(is_down(queue))
        self._up(queue)
        self.assertFalse(is_down(queue))
        return queue

    def _down(self, queue=None, installqueue=True, is_down=False,
              fsq_down=None, fsq_item_mode=None, fsq_item_user=None,
              fsq_item_group=None, **kwargs):
        if queue is None:
            queue = normalize()
        if fsq_down is not None:
            _c.FSQ_DOWN = fsq_down
        if installqueue == True:
            install(queue, is_down)
        if fsq_item_mode is not None:
            _c.FSQ_ITEM_MODE = fsq_item_mode
        if fsq_item_user is not None:
            _c.FSQ_ITEM_USER = fsq_item_user
        if fsq_item_group is not None:
            _c.FSQ_ITEM_GROUP = fsq_item_group
        down(queue, **kwargs)
        if fsq_item_user:
            kwargs['user'] = kwargs.get('user', fsq_item_user)
        if fsq_item_group:
            kwargs['group'] = kwargs.get('group', fsq_item_group)
        if fsq_item_mode:
            kwargs['mode'] = kwargs.get('mode', fsq_item_mode)
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
            for d in (getattr(_c, self._var), NOT_NORMAL[4], NON_ASCII,):
                for is_d in True, False:
                    # test normal cycle with a set down
                    queue = self._cycle(fsq_down=d, is_down=is_d)
                    # test that up doesn't throw an error if already up
                    up(queue)

                    # test with user id/group id and user name/group name
                    for uid, gid in ((UID, GID,), (UNAME, GNAME,)):
                        # just user kwarg
                        self._cycle(fsq_down=d, is_down=is_d, user=uid)
                        # just user set
                        self._cycle(fsq_down=d, is_down=is_d,
                                    fsq_item_user=uid)
                        # just group kwarg
                        self._cycle(fsq_down=d, is_down=is_d, group=gid)
                        # just group set
                        self._cycle(fsq_down=d, is_down=is_d,
                                    fsq_item_group=gid)
                        # both kwargs
                        self._cycle(fsq_down=d, is_down=is_d, user=uid,
                                    group=gid)
                        # both set
                        self._cycle(fsq_down=d, is_down=is_d,
                                    fsq_item_user=uid, fsq_item_group=gid)
                        for mode in MODES:
                            # just mode kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode)
                            # just mode set
                            self._cycle(fsq_down=d, is_down=is_d,
                                        fsq_item_mode=mode)
                            # mode and user kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        user=uid)
                            # mode and user set
                            self._cycle(fsq_down=d, is_down=is_d,
                                        fsq_item_mode=mode, fsq_item_user=uid)
                            # mode and group kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        group=gid)
                            # mode and group set
                            self._cycle(fsq_down=d, is_down=is_d,
                                        fsq_item_mode=mode,
                                        fsq_item_group=gid)
                            # mode and group and user kwarg
                            self._cycle(fsq_down=d, is_down=is_d, mode=mode,
                                        user=uid, group=gid)
                            # mode and group and user set
                            self._cycle(fsq_down=d, is_down=is_d,
                                        fsq_item_mode=mode, fsq_item_user=uid,
                                        fsq_item_group=gid)
                        # END mode LOOP
                    # END uid,gid LOOP
                # END is_down installed LOOP
            # END FSQ_DOWN loop
        # END root LOOP

    def test_invalidmode(self):
        '''Test invalid modes both set and passed'''
        self.assertRaises(TypeError, self._cycle, mode=ILLEGAL_MODE)
        self.assertRaises(TypeError, self._cycle,
                          fsq_item_mode=ILLEGAL_MODE)

    def test_invaliduidgid(self):
        '''Test invalid user and group ids and names'''
        # TEST ILLEGAL UID for User/Group set and passed
        self.assertRaises(FSQConfigError, self._cycle, user=ILLEGAL_UID)
        self.assertRaises(FSQConfigError, self._cycle,
                          fsq_item_group=ILLEGAL_UID)
        self.assertRaises(FSQConfigError, self._cycle, group=ILLEGAL_UID)
        self.assertRaises(FSQConfigError, self._cycle,
                          fsq_item_group=ILLEGAL_UID)
        self.assertRaises(FSQConfigError, self._cycle, user=ILLEGAL_UID,
                          group=ILLEGAL_UID)
        self.assertRaises(FSQConfigError, self._cycle,
                          fsq_item_user=ILLEGAL_UID,
                          fsq_item_group=ILLEGAL_UID)
        # TEST ILLEGAL UNAME for User/Group set and passed
        self.assertRaises(TypeError, self._cycle, user=ILLEGAL_UNAME)
        self.assertRaises(TypeError, self._cycle,
                          fsq_item_group=ILLEGAL_UNAME)
        self.assertRaises(TypeError, self._cycle, group=ILLEGAL_UNAME)
        self.assertRaises(TypeError, self._cycle,
                          fsq_item_group=ILLEGAL_UNAME)
        self.assertRaises(TypeError, self._cycle, user=ILLEGAL_UNAME,
                          group=ILLEGAL_UID)
        self.assertRaises(TypeError, self._cycle,
                          fsq_item_user=ILLEGAL_UNAME,
                          fsq_item_group=ILLEGAL_UNAME)

    def test_invalrootorqueue(self):
        '''Test proper failure for non-existant roots and non-existant
           queues'''
        # test invalid root or no queue
        for root in (NOROOT, ROOT1,):
            _c.FSQ_ROOT = root
            for fn in self._fns:
                self.assertRaises(FSQConfigError, fn, 'abc')

    def test_permdenied(self):
        '''Test proper failure for permission denied'''
        # test permission denied root
        queue = self._cycle()
        os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0)
        try:
            for fn in self._fns:
                self.assertRaises(self._perm, fn, queue)
        finally:
            os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0750)

    def test_invalnames(self):
        '''Test failure with invalid or illegal names'''
        for root in (ROOT1, ROOT2,):
            _c.FSQ_ROOT = root
            for name in ILLEGAL_NAMES:
                queue = self._cycle()
                setattr(_c, self._var, name)
                for fn in self._fns:
                    self.assertRaises(FSQPathError, fn, queue)

            queue = self._cycle()
            setattr(_c, self._var, ILLEGAL_NAME)
            for fn in self._fns:
                self.assertRaises(FSQCoerceError, fn, queue)

class TestTriggers(TestUpDownIsDown):
    '''Test the Triggers functions'''
    _fns = ( trigger, untrigger, trigger_pull, )
    _perm = (FSQTriggerPullError, FSQConfigError,)
    _var = 'FSQ_TRIGGER'
    def _cycle(self, queue=None, **kwargs):
        queue = self._trigger(queue, **kwargs)
        self.assertTrue(self._test_pull(queue))
        self._untrigger(queue)
        self.assertRaises(FSQTriggerPullError, self._test_pull, queue)
        return queue

    def _trigger(self, queue=None, installqueue=True, is_down=False,
                 fsq_down=None, fsq_item_mode=None, fsq_item_user=None,
                 fsq_item_group=None, **kwargs):
        # hack, as the tests are identical
        fsq_trigger = fsq_down
        del fsq_down
        if queue is None:
            queue = normalize()
        if fsq_trigger is not None:
            _c.FSQ_TRIGGER = fsq_trigger
        if installqueue == True:
            install(queue, is_down)
        if fsq_item_mode is not None:
            _c.FSQ_ITEM_MODE = fsq_item_mode
        if fsq_item_user is not None:
            _c.FSQ_ITEM_USER = fsq_item_user
        if fsq_item_group is not None:
            _c.FSQ_ITEM_GROUP = fsq_item_group
        trigger(queue, **kwargs)
        if fsq_item_user:
            kwargs['user'] = kwargs.get('user', fsq_item_user)
        if fsq_item_group:
            kwargs['group'] = kwargs.get('group', fsq_item_group)
        if fsq_item_mode:
            kwargs['mode'] = kwargs.get('mode', fsq_item_mode)
        self.assertTrue(_valid_trigger(queue, **kwargs))
        return queue

    def _untrigger(self, queue):
        untrigger(queue)
        self.assertTrue(_valid_untrigger(queue))

    def _test_pull(self, queue):
        t_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_TRIGGER)
        # test with no listener
        trigger_pull(queue, ignore_listener=True)
        # test raise with no listener
        self.assertRaises(FSQTriggerPullError, trigger_pull, queue)
        # ghetto trigger-listen emulator; man 1 trigger-listen
        fd2 = None
        fd = os.open(t_path, os.O_RDONLY|os.O_NDELAY|os.O_NONBLOCK)
        try:
            # keep the FIFO open even when write side closes
            fd2 = os.open(t_path, os.O_WRONLY|os.O_NDELAY|os.O_NONBLOCK)
            trigger_pull(queue)
            res = os.read(fd, 1)
            if res == '\0':
                return True
            return False
        finally:
            os.close(fd)
            if fd2 is not None:
                os.close(fd2)
