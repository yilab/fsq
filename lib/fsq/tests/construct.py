import os
from . import FSQTestCase
from .internal import test_type_own_mode, normalize
from . import constants as _test_c

# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import construct, deconstruct, constants as _c, FSQPathError,\
               FSQCoerceError, FSQEncodeError, FSQMalformedEntryError

class TestConstruct(FSQTestCase):
    def _cycle(self, args, fsq_encode=None, fsq_delimiter=None,
               assert_eq=True):
        normalize()
        if fsq_encode is not None:
            _c.FSQ_ENCODE = fsq_encode
        if fsq_delimiter is not None:
            _c.FSQ_DELIMITER = fsq_delimiter
        constructed = construct(args)
        delim, deconstructed = deconstruct(constructed)
        if assert_eq:
            self.assertFalse(bool(len(set(args)^set(deconstructed))))
            self.assertEquals(delim, _c.FSQ_DELIMITER)
        return deconstructed

    def test_basic(self):
        for encodeseq, delimiter in ( _test_c.ORIG_ENCODE_DELIMITER,
                                    ( _test_c.ENCODE, _test_c.DELIMITER, )):
            for args in (_test_c.NORMAL, ( _c.FSQ_DELIMITER.join(
                                               _test_c.NORMAL),
                                           _c.FSQ_ENCODE.join(_test_c.NORMAL),
                                           _c.FSQ_ENCODE.join([
                                               _test_c.NON_ASCII]*2), ),
                                           _test_c.ILLEGAL_NAMES):
                # one set, then the other, then both
                self._cycle(args, fsq_encode=encodeseq)
                self._cycle(args, fsq_delimiter=delimiter)
                self._cycle(args, fsq_encode=encodeseq,
                            fsq_delimiter=delimiter)

        # int coerce
        against = [unicode(i) for i in _test_c.MODES]
        deconstructed = self._cycle(_test_c.MODES, assert_eq=False)
        self.assertFalse(bool(len(set(against)^set(deconstructed))))
        # float coerce
        against = [unicode(float(i)) for i in _test_c.MODES]
        deconstructed = self._cycle([float(i) for i in _test_c.MODES],
                                    assert_eq=False)
        self.assertFalse(bool(len(set(against)^set(deconstructed))))

    def test_badconstruct(self):
        # assert failure for bad encode char
        normalize()
        _c.FSQ_ENCODE = _test_c.ILLEGAL_ENCODE
        self.assertRaises(FSQEncodeError, construct, _test_c.NORMAL)
        normalize()
        _c.FSQ_ENCODE = _test_c.ILLEGAL_NAME
        self.assertRaises(FSQCoerceError, construct, _test_c.NORMAL)

        # assert failure for non coercable arg
        normalize()
        self.assertRaises(FSQCoerceError, construct, [_test_c.ILLEGAL_NAME])

        # non-ascii encodeseq
        normalize()
        _c.FSQ_ENCODE = _test_c.NON_ASCII
        self.assertRaises(FSQEncodeError, construct, _test_c.NORMAL)

        # non-ascii delimiter
        normalize()
        _c.FSQ_DELIMITER = _test_c.NON_ASCII
        self.assertRaises(FSQEncodeError, construct, _test_c.NORMAL)

        # delimiter and encodeseq set to be same
        normalize()
        _c.FSQ_DELIMITER = _c.FSQ_ENCODE
        self.assertRaises(FSQEncodeError, construct, _test_c.NORMAL)

    def test_baddecode(self):
        # assert failure for bad encode char
        ok_constructed = construct(_test_c.NORMAL)
        normalize()
        _c.FSQ_ENCODE = _test_c.ILLEGAL_ENCODE
        self.assertRaises(FSQEncodeError, deconstruct, ok_constructed)
        normalize()
        _c.FSQ_ENCODE = _test_c.ILLEGAL_NAME
        self.assertRaises(FSQCoerceError, deconstruct, ok_constructed)

        # non-ascii encodeseq
        normalize()
        _c.FSQ_ENCODE = _test_c.NON_ASCII
        self.assertRaises(FSQEncodeError, deconstruct, ok_constructed)

        # incomplete finishing seq
        normalize()
        self.assertRaises(FSQEncodeError, deconstruct,
                          _c.FSQ_DELIMITER.join([ u'', _test_c.NORMAL[0],
                                                  _c.FSQ_ENCODE ]))

        # invalid delimiter
        normalize()
        self.assertRaises(FSQEncodeError, deconstruct,
                          _test_c.NON_ASCII.join([ u'', _test_c.NORMAL[0] ]))

        # encoded non-ascii
        normalize()
        bad_val = u''.join([_c.FSQ_ENCODE, hex(ord(_test_c.NON_ASCII))])
        self.assertRaises(FSQEncodeError, deconstruct,
                          _c.FSQ_DELIMITER.join([u'', bad_val]))

        normalize()
        self.assertRaises(FSQMalformedEntryError, deconstruct, u'')

        # non coercable passed as arg
        normalize()
        self.assertRaises(FSQCoerceError, deconstruct, _test_c.NORMAL)
