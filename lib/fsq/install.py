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

from . import FSQ_TMP, FSQ_QUEUE, FSQ_DONE, FSQ_DOWN, FSQ_ROOT,\
              FSQ_QUEUE_USER, FSQ_QUEUE_GROUP, FSQ_QUEUE_MODE, FSQ_ITEM_USER,\
              FSQ_ITEM_GROUP, FSQ_ITEM_MODE, FSQ_UNINSTALL_WAIT, FSQ_LOCK,\
              path as fsq_path, FSQInstallError, down as fsq_down
from .internal import coerce_unicode, uid_gid, wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
def _cleanup(clean_dir):
    try:
        os.rmdir(clean_dir)
    except (OSError, IOError, ), e:
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
    try:
        tmp_queue = tempfile.mkdtemp(u'', u''.join([u'.', trg_queue]), root)
        return tmp_queue, os.path.basename(tmp_queue)
    except (OSError, IOError, ), e:
        if e.errno != EEXIST:
            _cleanup(tmp_queue)

####### EXPOSED METHODS #######
def install(trg_queue, is_down=False, root=FSQ_ROOT, done=FSQ_DONE,
            tmp=FSQ_TMP, queue=FSQ_QUEUE, user=FSQ_QUEUE_USER,
            group=FSQ_QUEUE_GROUP, mode=FSQ_QUEUE_MODE, down=FSQ_DOWN,
            down_user=FSQ_ITEM_USER, down_group=FSQ_ITEM_GROUP,
            down_mode=FSQ_ITEM_MODE):
    '''Atomically install a queue'''

    # validate here, so that we don't throw an odd exception on the tmp name
    trg_queue = fsq_path.valid_name(trg_queue)
    tmp_full, tmp_queue = _tmp_trg(trg_queue, root)
    # only do a password lookup once
    if user is not None or group is not None:
        uid, gid = uid_gid(user, group)
        if user is not None:
            user = uid
        if group is not None:
            group = gid
    try:
        # open once to cut down on stat/open for chown/chmod combo
        fd = os.open(tmp_full, os.O_RDONLY)
        try:
            os.fchmod(fd, mode)
            # always chown here as mkdtemp plays differently than normal mkdir
            os.fchown(fd, *uid_gid(user, group))
        finally:
            os.close(fd)

        # bless our queue with its children
        _instdir(fsq_path.tmp(tmp_queue, root=root, tmp=tmp), mode, user,
                              group)
        _instdir(fsq_path.queue(tmp_queue, root=root, queue=queue), mode,
                                user, group)
        _instdir(fsq_path.done(tmp_queue, root=root, done=done), mode, user,
                               group)

        # down via configure.down if necessary
        if is_down:
            fsq_down(tmp_queue, root=root, down=down, user=down_user,
                     group=down_group, mode=down_mode)

        # atomic commit -- by rename
        os.rename(tmp_full, fsq_path.base(trg_queue, root=root))
    except (OSError, IOError, ), e:
        uninstall(tmp_queue, root=root, done=done, tmp=tmp, queue=queue,
                  down=down, down_user=down_user, down_group=down_group,
                  down_mode=down_mode)
        if e.errno == errno.ENOTEMPTY:
            raise FSQInstallError(e.errno, u'queue exists: {0}'.format(
                                  trg_queue))
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

def uninstall(trg_queue, root=FSQ_ROOT, done=FSQ_DONE, tmp=FSQ_TMP,
              queue=FSQ_QUEUE, down=FSQ_DOWN, down_user=FSQ_ITEM_USER,
              down_group=FSQ_ITEM_GROUP, down_mode=FSQ_ITEM_MODE,
              lock=FSQ_LOCK):
    '''Idempotently uninstall a queue'''
    # immediately down the queue
    fsq_down(trg_queue, root=root, down=down, user=down_user,
             group=down_group, mode=down_mode)
    # atomically mv our queue to a reserved target so we can recursively
    # remove without prying eyes
    try:
        os.rename(fsq_path.base(trg_queue, root=root), tmp_full)
        # this makes me uneasy ... but here we go magick
        shutil.rmtree(tmp_full)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQInstallError(e.errno, u'no such queue:'\
                                  ' {0}'.format(trg_queue))
        raise FSQInstallError(e.errno, wrap_io_os_err(e))
