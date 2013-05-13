# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
# @author: Jeff Rand <jeff.rand@axial.net>
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
              down, trigger, down_host, host_trigger
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

def _instdir(trg_dir, mode, uid, gid):
    try:
        os.mkdir(trg_dir, mode)
        fd = os.open(trg_dir, os.O_RDONLY)
        try:
            os.fchmod(fd, mode)
            # os.chown is non-atomic, prefer open/fchown as a best practice
            if -1 != uid or -1 != gid:
                os.fchown(fd, uid, gid)
        finally:
            os.close(fd)
    except (OSError, IOError, ), e:
        _cleanup(trg_dir)
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

# make a hidden tmp target queue
def _tmp_trg(trg_queue, root=_c.FSQ_ROOT):
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

def _remove_dir(path, tmp_full, trg_queue):
    # atomically mv our queue to a reserved target so we can recursively
    # remove without prying eyes
    try:
        os.rename(path, tmp_full)
        # this makes me uneasy ... but here we go magick
        shutil.rmtree(tmp_full)
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQInstallError(e.errno, u'no such queue:'\
                                  ' {0}'.format(trg_queue))
        if isinstance(e, FSQError):
            raise e
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

# setup default modes and users
def _def_mode(mode, user, group, item_user, item_group, item_mode):
    mode = _c.FSQ_QUEUE_MODE if mode is None else mode
    user = _c.FSQ_QUEUE_USER if user is None else user
    group = _c.FSQ_QUEUE_GROUP if group is None else group
    item_user = _c.FSQ_ITEM_USER if item_user is None else item_user
    item_group = _c.FSQ_ITEM_GROUP if item_group is None else item_group
    item_mode = _c.FSQ_ITEM_MODE if mode is None else item_mode
    return mode, user, group, item_user, item_group, item_mode

####### EXPOSED METHODS #######
def install(trg_queue, is_down=False, is_triggered=False, user=None,
            group=None, mode=None, item_user=None, item_group=None,
            item_mode=None, hosts=None, is_host_triggered=False):
    '''Atomically install a queue'''
    mode, user, group, item_user, item_group, item_mode =\
        _def_mode(mode, user, group, item_user, item_group, item_mode)
    if hosts and not hasattr(hosts, '__iter__'):
        raise TypeError('Hosts must be an interable')
    # validate here, so that we don't throw an odd exception on the tmp name
    trg_queue = fsq_path.valid_name(trg_queue)
    # uid_gid makes calls to the pw db and|or gr db, in addition to
    # potentially stat'ing, as such, we want to avoid calling it unless we
    # absoultely have to
    uid, gid = uid_gid(user, group)
    tmp_full, tmp_queue = _tmp_trg(trg_queue, _c.FSQ_ROOT)
    try:
        # open once to cut down on stat/open for chown/chmod combo
        fd = os.open(tmp_full, os.O_RDONLY)
        try:
            # always fchmod here as mkdtemp is different than normal mkdir
            os.fchmod(fd, mode)
            if -1 != uid or -1 != gid:
                os.fchown(fd, uid, gid)
        finally:
            os.close(fd)

        # bless our queue with its children
        _instdir(fsq_path.tmp(tmp_queue), mode, uid, gid)
        _instdir(fsq_path.queue(tmp_queue), mode, uid, gid)
        _instdir(fsq_path.done(tmp_queue), mode, uid, gid)
        _instdir(fsq_path.fail(tmp_queue), mode, uid, gid)

        # down via configure.down if necessary
        if is_down:
            down(tmp_queue, user=item_user, group=item_group, mode=item_mode)
        if is_triggered or _c.FSQ_USE_TRIGGER:
            trigger(tmp_queue, user=item_user, group=item_group,
                    mode=item_mode)

        # atomic commit -- by rename
        os.rename(tmp_full, fsq_path.base(trg_queue))
    except (OSError, IOError, ), e:
        shutil.rmtree(tmp_full)
        if e.errno == errno.ENOTEMPTY:
            raise FSQInstallError(e.errno, u'queue exists: {0}'.format(
                                  trg_queue))
        if isinstance(e, FSQError):
            raise e
        raise FSQInstallError(e.errno, wrap_io_os_err(e))

    if hosts:
        install_host(trg_queue, *hosts, is_down=is_down, user=user,
                     group=group, mode=mode, item_user=item_user,
                     item_group=item_group, item_mode=item_mode)
    if is_host_triggered:
       host_trigger(trg_queue, user=user, group=group, mode=mode)

def uninstall(trg_queue, item_user=None, item_group=None, item_mode=None):
    '''Idempotently uninstall a queue, should you want to subvert FSQ_ROOT
       settings, merely pass in an abolute path'''
    # immediately down the queue
    try:
        down(trg_queue, user=item_user, group=item_group,
             mode=(_c.FSQ_ITEM_MODE if item_mode is None else item_mode))
    except FSQError, e:
        raise FSQInstallError(e.errno, wrap_io_os_err(e))
    tmp_full, tmp_queue = _tmp_trg(trg_queue, _c.FSQ_ROOT)
    _remove_dir(fsq_path.base(trg_queue), tmp_full, trg_queue)

def uninstall_host(trg_queue, *hosts, **kwargs):
    '''Idempotently uninstall a host queue, should you want to subvert FSQ_ROOT
       settings, merely pass in an abolute path'''
    # immediately down the queue
    item_user = kwargs.pop('item_user', None)
    item_group = kwargs.pop('item_group', None)
    item_mode = kwargs.pop('item_mode', None)
    for host in hosts:
    # immediately down the queue
        try:
            down_host(trg_queue, host, user=item_user, group=item_group,
                 mode=(_c.FSQ_ITEM_MODE if item_mode is None else item_mode))
        except FSQError, e:
            raise FSQInstallError(e.errno, wrap_io_os_err(e))
        tmp_full, tmp_queue = _tmp_trg(host, fsq_path.hosts(trg_queue))
        _remove_dir(fsq_path.base(trg_queue, host), tmp_full, trg_queue)

def install_host(trg_queue, *hosts, **kwargs):
    ''' Atomically install host queues '''
    user = kwargs.pop('user', None)
    group = kwargs.pop('group', None)
    mode = kwargs.pop('mode', None)
    item_user = kwargs.pop('item_user', None)
    item_group = kwargs.pop('item_group', None)
    item_mode = kwargs.pop('item_mode', None)
    is_down = kwargs.pop('is_down', False)

    #set modes
    mode, user, group, item_user, item_group, item_mode =\
        _def_mode(mode, user, group, item_user, item_group, item_mode)
    uid, gid = uid_gid(user, group)
    host_path = fsq_path.hosts(trg_queue)
    try:
        _instdir(host_path, mode, uid, gid)
    except (OSError, IOError, ), e:
        if e.errno not in ( errno.EEXIST, errno.ENOTEMPTY, ):
            raise FSQInstallError(e.errno, wrap_io_os_err(e))
    if hosts:
        for host in hosts:
            host = fsq_path.valid_name(host)
            # uid_gid makes calls to the pw db and|or gr db, in addition to
            # potentially stat'ing, as such, we want to avoid calling it
            # unless we absoultely have to
            uid, gid = uid_gid(user, group)
            tmp_full, tmp_queue = _tmp_trg(host, host_path)
            try:
                # open once to cut down on stat/open for chown/chmod combo
                fd = os.open(tmp_full, os.O_RDONLY)
                try:
                    # always fchmod here as mkdtemp is different than normal
                    # mkdir
                    os.fchmod(fd, mode)
                    if -1 != uid or -1 != gid:
                        os.fchown(fd, uid, gid)
                finally:
                    os.close(fd)

                # bless our queue with its children
                _instdir(fsq_path.tmp(trg_queue, tmp_queue), mode, uid, gid)
                _instdir(fsq_path.queue(trg_queue, tmp_queue), mode, uid, gid)
                _instdir(fsq_path.done(trg_queue, tmp_queue), mode, uid, gid)
                _instdir(fsq_path.fail(trg_queue, tmp_queue), mode, uid, gid)

                # down via configure.down if necessary
                if is_down:
                    down_host(tmp_queue, host, user=item_user,
                              group=item_group, mode=item_mode)

                # atomic commit -- by rename
                os.rename(tmp_full, fsq_path.base(trg_queue, host))
            except (OSError, IOError, ), e:
                shutil.rmtree(tmp_full)
                if e.errno == errno.ENOTEMPTY:
                    raise FSQInstallError(e.errno, u'queue exists: {0}'.format(
                                          trg_queue))
                if isinstance(e, FSQError):
                    raise e
