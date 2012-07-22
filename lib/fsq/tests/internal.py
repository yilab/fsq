from . import constants as _test_c
from .. import constants as _c

def normalize():
    '''Set FSQ config (aside from FSQ_ROOT) back to normal'''
    _c.FSQ_QUEUE, _c.FSQ_TMP, _c.FSQ_DONE = _test_c.NORMAL[:3]
    _c.FSQ_FAIL, _c.FSQ_DOWN, _c.FSQ_TRIGGER = _test_c.NORMAL[3:]
    _c.FSQ_QUEUE_USER, _c.FSQ_QUEUE_GROUP = _test_c.ORIG_QUEUE_UG
    _c.FSQ_ITEM_USER, _c.FSQ_ITEM_GROUP = _test_c.ORIG_ITEM_UG
    _c.FSQ_QUEUE_MODE, _c.FSQ_ITEM_MODE = _test_c.ORIG_MODES
    _test_c.COUNT += 1
    return _test_c.TEST_QUEUE.format(_test_c.COUNT)

def test_type_own_mode(st, t_path, f_type, uid, gid, mode):
    '''Test a stated file path against an expected type, ownership user and
       group and mode'''
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
