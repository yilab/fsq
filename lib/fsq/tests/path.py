import os
from . import FSQTestCase
from .internal import test_type_own_mode, normalize
from . import constants as _test_c

# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import path as _p, constants as _c, FSQPathError, FSQCoerceError

########## INTERNAL VALIDATION METHODS
def _valid_path(*args):
    return os.path.join(_c.FSQ_ROOT, *args)

########## EXPOSED TEST CASES
class TestPath(FSQTestCase):
    def _gammit(self, verifier, v_args, fn, *args):
        for i in _test_c.NORMAL + _test_c.NOT_NORMAL +\
                tuple([_test_c.NON_ASCII]):
            _test_c.COUNT += 1
            self.assertEquals(fn(i, *args), verifier(i, *v_args))
            # verify string coerce
            _test_c.COUNT += 1
            self.assertEquals(fn(i.encode('utf8'), *args), verifier(i,
                              *v_args))
        for i in _test_c.ILLEGAL_NAMES:
            _test_c.COUNT += 1
            self.assertRaises(FSQPathError, fn, i, *args)
        for i in _test_c.MODES:
            _test_c.COUNT += 1
            # verify integer coerce
            self.assertEquals(fn(i, *args), verifier(unicode(i), *v_args))
            _test_c.COUNT += 1
            # verify float coerce
            self.assertEquals(fn(float(i), *args), verifier(unicode(float(i)),
                              *v_args))

        _test_c.COUNT += 1
        # verify non-coercable char yields coerce-error
        self.assertRaises(FSQCoerceError, fn, _test_c.ILLEGAL_NAME, *args)

    def _second_level_test(self, fn, const, do_item=False):
        for root in ( _test_c.ROOT1, _test_c.ROOT2, ):
            _c.FSQ_ROOT = root
            for val in _test_c.NORMAL:
                setattr(_c, const, val)
                if do_item:
                    for item in _test_c.NORMAL:
                        self._gammit(_valid_path, [ val, item, ], fn, item)
                else:
                    self._gammit(_valid_path, [ val, ], fn)

        # verify failure on thing set to non-allowed name
        for val in _test_c.ILLEGAL_NAMES:
            normalize()
            setattr(_c, const, val)
            if do_item:
                self.assertRaises(FSQPathError, fn, *_test_c.NORMAL[:2])
                normalize()
                self.assertRaises(FSQPathError, fn, _test_c.NORMAL[0], val)
            else:
                self.assertRaises(FSQPathError, fn, _test_c.NORMAL[0])

        # verify illegal name for thing on non-coercable name
        normalize()
        setattr(_c, const, _test_c.ILLEGAL_NAME)
        if do_item:
            self.assertRaises(FSQCoerceError, fn, *_test_c.NORMAL[:2])
            normalize()
            self.assertRaises(FSQCoerceError, fn, _test_c.NORMAL[0],
                              _test_c.ILLEGAL_NAME)
        else:
            self.assertRaises(FSQCoerceError, fn, _test_c.NORMAL[0])


    def test_valid_name(self):
        self._gammit(lambda x:x, [], _p.valid_name)

    def test_base(self):
        for root in ( _test_c.ROOT1, _test_c.ROOT2, ):
            _c.FSQ_ROOT = root
            self._gammit(_valid_path, [], _p.base)

    def test_tmp(self):
        self._second_level_test(_p.tmp, 'FSQ_TMP')

    def test_queue(self):
        self._second_level_test(_p.queue, 'FSQ_QUEUE')

    def test_fail(self):
        self._second_level_test(_p.fail, 'FSQ_FAIL')

    def test_done(self):
        self._second_level_test(_p.done, 'FSQ_DONE')

    def test_down(self):
        self._second_level_test(_p.down, 'FSQ_DOWN')

    def test_trigger(self):
        self._second_level_test(_p.trigger, 'FSQ_TRIGGER')

    def test_item(self):
        self._second_level_test(_p.item, 'FSQ_QUEUE', do_item=True)
