# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/enqueue.py -- provides queue (un)install functions: install, uninstall
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno
import tempfile
import shutil

from . import constants as _c, path as fsq_path, FSQInstallError, FSQError,\
              down, trigger
from .internal import uid_gid, wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
def _cleanup(clean_dir):
    try:
        os.rmdir(clean_dir)
    except (OSError, IOError, ), e:
        # suppress ENOENT, as we don't care if we can't remove something that
        # wasn't there, we only care that it isn't there.
        if e.errno != errno.ENOENT:
            raise FSQInstallError(e.errno, wrap_io_os_err(e))

def _instdir(trg_dir, mode, user, group):
    try:
        os.mkdir(trg_dir, mode)
        # os.chown is non-atomic, prefer open/fchown as a best practice
        fd = os.open(trg_dir, os.O_RDONLY)
        try:
            if user is not None or group is not None:
                os.fchown(fd, *uid_gid(user, group, fd=fd))
        finally:
            os.close(fd)
    except (OSError, IOError, ), e:
        _cleanup(trg_dir)
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

# make a hidden tmp target queue
def _tmp_trg(trg_queue, root):
    tmp_queue = None
    try:
        tmp_queue = tempfile.mkdtemp(u'', u''.join([u'.', trg_queue]), root)
        return tmp_queue, os.path.basename(tmp_queue)
    except Exception, e:
        if tmp_queue is not None:
            _cleanup(tmp_queue)
        if isinstance(e, ( OSError, IOError, )):
            raise FSQInstallError(e.errno, u': '.join([
                u'cannot mkdtemp: {0}'.format(trg_queue),
                wrap_io_os_err(e)
            ]))
        raise e

####### EXPOSED METHODS #######
def install(trg_queue, is_down=False, is_triggered=False, user=None,
            group=None, mode=None, item_user=None, item_group=None,
            item_mode=None):
    '''Atomically install a queue'''
    # setup default modes and users
    mode = _c.FSQ_QUEUE_MODE if mode is None else mode
    user = _c.FSQ_QUEUE_USER if user is None else user
    group = _c.FSQ_QUEUE_GROUP if group is None else group
    item_user = _c.FSQ_ITEM_USER if item_user is None else item_user
    item_group = _c.FSQ_ITEM_GROUP if item_group is None else item_group
    item_mode = _c.FSQ_ITEM_MODE if mode is None else item_mode

    # validate here, so that we don't throw an odd exception on the tmp name
    trg_queue = fsq_path.valid_name(trg_queue)
    tmp_full, tmp_queue = _tmp_trg(trg_queue, _c.FSQ_ROOT)
    # uid_gid makes calls to the pw db and|or gr db, in addition to
    # potentially stat'ing, as such, we want to avoid calling it unless we
    # absoultely have to
    if user is not None or group is not None:
        uid, gid = uid_gid(user, group)
        user = user if user is None else uid
        group = group if group is None else gid
    try:
        # open once to cut down on stat/open for chown/chmod combo
        fd = os.open(tmp_full, os.O_RDONLY)
        try:
            os.fchmod(fd, mode)
            # always fchown here as mkdtemp is different than normal mkdir
            os.fchown(fd, *uid_gid(user, group))
        finally:
            os.close(fd)

        # bless our queue with its children
        _instdir(fsq_path.tmp(tmp_queue), mode, user, group)
        _instdir(fsq_path.queue(tmp_queue), mode, user, group)
        _instdir(fsq_path.done(tmp_queue), mode, user, group)
        _instdir(fsq_path.fail(tmp_queue), mode, user, group)

        # down via configure.down if necessary
        if is_down:
            down(tmp_queue, user=item_user, group=item_group, mode=item_mode)
        if is_triggered or _c.FSQ_USE_TRIGGER:
            trigger(tmp_queue, user=item_user, group=item_group,
                    mode=item_mode)

        # atomic commit -- by rename
        os.rename(tmp_full, fsq_path.base(trg_queue))
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOTEMPTY:
            raise FSQInstallError(e.errno, u'queue exists: {0}'.format(
                                  trg_queue))
        shutil.rmtree(tmp_full)
        if isinstance(e, FSQError):
            raise e
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

def uninstall(trg_queue, item_user=None, item_group=None, item_mode=None):
    '''Idempotently uninstall a queue, should you want to subvert FSQ_ROOT
       settings, merely pass in an abolute path'''
    # atomically mv our queue to a reserved target so we can recursively
    # remove without prying eyes
    try:
        # immediately down the queue
        down(trg_queue, user=item_user, group=item_group,
             mode=(_c.FSQ_ITEM_MODE if item_mode is None else item_mode))
        tmp_full, tmp_queue = _tmp_trg(trg_queue, _c.FSQ_ROOT)
        os.rename(fsq_path.base(trg_queue), tmp_full)
        # this makes me uneasy ... but here we go magick
        shutil.rmtree(tmp_full)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQInstallError(e.errno, u'no such queue:'\
                                  ' {0}'.format(trg_queue))
        if isinstance(e, FSQError):
            raise e
        raise FSQInstallError(e.errno, wrap_io_os_err(e))
