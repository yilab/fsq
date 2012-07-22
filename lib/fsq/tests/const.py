import numbers

from . import FSQTestCase
from .internal import normalize
from .constants import ROOT1, ROOT2, NON_ASCII, NOT_NORMAL, ILLEGAL_NAMES,\
                       ILLEGAL_MODE, ILLEGAL_NAME, ILLEGAL_UID,\
                       ILLEGAL_UNAME, ORIG_QUEUE_UG, ORIG_ITEM_UG, MODES,\
                       STR_MODES, UID, GID, UNAME, GNAME, NOROOT, NOCONST

# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import FSQEnvError, FSQCoerceError, const, set_const, constants as _c

########### EXPOSED TEST CASES
class TestConsts(FSQTestCase):
    def test_const(self):
        for i in dir(_c):
            if i.startswith('FSQ_'):
                normalize()
                self.assertEquals(getattr(_c, i), const(i))
        normalize()
        self.assertRaises(FSQEnvError, const, NOCONST)
        normalize()
        self.assertRaises(TypeError, const, ILLEGAL_NAME)

    def test_setconst(self):
        for i in dir(_c):
            # test setting modes
            orig_val = const(i)
            try:
                if i.startswith('FSQ_'):
                    if i.endswith('MODE'):
                        for mode in MODES:
                            normalize()
                            self.assertEquals(set_const(i, mode), mode)
                            self.assertEquals(mode, const(i))
                        for mode in STR_MODES:
                            normalize()
                            i_mode = int(mode, 8)
                            self.assertEquals(set_const(i, mode), i_mode)
                            self.assertEquals(i_mode, const(i))

                        normalize()
                        setattr(_c, i, orig_val)
                        self.assertRaises(FSQEnvError, set_const, i,
                                          ILLEGAL_MODE)
                        self.assertEquals(const(i), orig_val)

                    elif isinstance(const(i), numbers.Integral):
                        # a bunch of things that can become an int
                        for j in (0, 1L, True, False, '8888888', ):
                            normalize()
                            self.assertEquals(set_const(i, j), int(j))
                            self.assertEquals(int(j), const(i))

                        # and one thing that cannot
                        normalize()
                        setattr(_c, i, orig_val)
                        self.assertRaises(FSQEnvError, set_const, i,
                                          ILLEGAL_MODE)
                        self.assertEquals(const(i), orig_val)
                    else:
                        for j in NOT_NORMAL:
                            normalize()
                            ret = set_const(i, j)
                            self.assertEquals(const(i), ret)
                            s_version = str(j)
                            ret = set_const(i, s_version)
                            self.assertEquals(const(i), ret)

                        normalize()
                        self.assertEquals(set_const(i, NON_ASCII), NON_ASCII)
                        self.assertEquals(const(i), NON_ASCII)
                        normalize()
                        setattr(_c, i, orig_val)
                        self.assertRaises(FSQCoerceError, set_const, i,
                                          ILLEGAL_UNAME)
                        self.assertEquals(const(i), orig_val)
            finally:
                setattr(_c, i, orig_val)

        # test setting invalid
        normalize()
        self.assertRaises(FSQEnvError, set_const, NOCONST, 'hi')
        normalize()
        self.assertRaises(TypeError, set_const, ILLEGAL_NAME, 'hi')
