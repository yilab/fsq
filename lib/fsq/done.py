# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/enqueue.py -- provides finishing functions: done, fail, fail_tmp,
#                   fail_perm, retry
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import os
import errno
import datetime
from . import FSQ_MAX_TRIES, FSQ_TTL, FSQ_ROOT, FSQ_DONE, FSQ_TMP, FSQ_QUEUE,\
              FSQ_FAIL, FSQ_FAIL_TMP, FSQ_SUCCESS, FSQ_FAIL_PERM,\
              FSQWorkItemError, FSQFailError, FSQEnqueueMaxTriesError,\
              FSQMaxTriesError, FSQTTLExpiredError, path as fsq_path, mkitem
from .internal import wrap_io_os_err, check_ttl_max_tries

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
def _unlink(item_src, e_class=FSQFailError):
    try:
        os.unlink(item_src)
    except (OSError, IOError, ), e:
        if e.errno != errno.ENOENT:
            raise e_class(e.errno, u':'.join([
                wrap_io_os_err(e),
                u'cannot unlink failed item from queue: {0}'.format(item_src)
            ]))

# these functions are underscored to avoid name collisions with kwargs
def _fail_tmp(item, queue=None, root=None, max_tries=None,
              ttl=None, fail_perm=None):
    '''Try to fail a work-item temporarily (up recount and keep in queue),
       if max tries or ttl is exhausted, escalate to permanant failure.'''
    try:
        max_tries = item.max_tries if max_tries is None else max_tries
        ttl = item.ttl if ttl is None else ttl
        root = item.root if root is None else root
        queue = item.queue_dir if queue is None else queue
        trg_queue = item.queue
        tmp = item.tmp_dir
        tries = item.tries+1
        enqueued_at = item.enqueued_at
        fail_perm = item.fail_perm_code if fail_perm is None else fail_perm
        check_ttl_max_tries(tries, enqueued_at, max_tries, ttl, fail_perm)
        item_src = fsq_path.item(trg_queue, item.id, root=root, queue=queue)
        # mv to tmp, then mv back into queue
        trg_path, discard = mkitem(fsq_path.tmp(trg_queue, root=root,
                                   tmp=tmp), item.arguments,
                                   now=enqueued_at, pid=item.pid,
                                   tries=tries, link_src=item_src)
        _unlink(item_src)
        re_src, discard = mkitem(fsq_path.queue(trg_queue, root=root,
                                 queue=queue), item.arguments,
                                 now=enqueued_at, pid=item.pid,
                                 tries=tries, link_src=trg_path)
        _unlink(trg_path)
        return os.path.basename(re_src)
    except AttributeError, e:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))
    except (FSQMaxTriesError, FSQTTLExpiredError,), e:
        _fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'for item {0}; failed permanantly'.format(item.id),
        ])
        raise e
    except FSQEnqueueMaxTriesError, e:
        _fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'cannot enqueue retry for item',
            u' {0}; failed permanantly'.format(item.id)
        ])
        raise e

def _fail_perm(item, queue=FSQ_QUEUE, root=FSQ_ROOT, fail=FSQ_FAIL):
    '''Fail a work-item permanatly by mv'ing it to queue's fail directory'''
    try:
        # The only thing we require to fail is an item_id and a queue
        # as an item may fail permanantly due to malformed item_id-ness
        queue = getattr(item, 'queue_dir', queue)
        fail = getattr(item, 'fail_dir', fail)
        root = getattr(item, 'root', root)
        arguments = getattr(item, 'arguments', [])
        now = getattr(item, 'enqueued_at', datetime.datetime.now())
        pid = getattr(item, 'pid', os.getpid())
        tries = getattr(item, 'tries', 0)
        item_id = item.id
        trg_queue = item.queue
    except AttributeError, e:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))

    # this methodology may result in items being in both fail and queue
    # but will guarentee uniqueness in the fail directory
    item_src = fsq_path.item(trg_queue, item_id, root=root, queue=queue)
    trg_path, discard = mkitem(fsq_path.fail(trg_queue, root=root, fail=fail),
                               arguments, now=now, pid=pid, tries=tries,
                               link_src=item_src)
    _unlink(item_src)
    return os.path.basename(trg_path)

def _done(item, done_type=None, success=None, fail_tmp=None, fail_perm=None,
          queue=None, done=None, fail=None, max_tries=None, ttl=None):
    '''Wrapper for any type of finish, successful, permanant failure or
       temporary failure'''
    success = item.success if success is None else success
    if done_type is None or done_type == success:
        return _success(item, done=done, queue=queue, root=root,
                        fail_perm=fail_perm)
    return _fail(item, fail_type=fail_type, queue=queue, root=root, fail=fail,
                 fail_tmp=fail_tmp, fail_perm=fail_perm, max_tries=max_tries,
                 ttl=ttl)

def _fail(item, fail_type=None, queue=None, root=None, fail=None,
          fail_tmp=None, fail_perm=None, max_tries=None, ttl=None):
    '''Fail a work item, either temporarily or permanantly'''
    # default to fail_perm
    if fail_type is not None and fail_type == fail_tmp:
        return _fail_tmp(item, max_tries=max_tries, ttl=ttl,
                         fail_perm=fail_perm)
    return _fail_perm(item, queue=queue, root=root, fail=fail)

def _success(item, done=None, queue=None, root=None):
    '''Successful finish'''
    try:
        done = item.done_dir if done is None else done
        queue = item.queue_dir if queue is None else queue
        root = item.root if root is None else root
        enqueued_at = item.enqueued_at
        trg_queue = item.queue
        # mv to done
        item_src = fsq_path.item(trg_queue, item.id, root=root, queue=queue)
        trg_path, discard = mkitem(fsq_path.done(trg_queue, root=root,
                                   done=done), item.arguments,
                                   now=item.enqueued_at, pid=item.pid,
                                   tries=item.tries, link_src=item_src)
        _unlink(item_src)
    except AttributeError, e:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))
    except FSQEnqueueMaxTriesError, e:
        _fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'cannot mark item completed',
            u' {0}; failed permanantly'.format(item.id)
        ])
        raise e

####### EXPOSED METHODS #######
def retry(*args, **kwargs):
    '''Retry is a convenience alias for fail_tmp'''
    return _fail_tmp(*args, **kwargs)

# expose internal methods that are internal for name-collision purposes
fail_tmp = _fail_tmp
fail_perm = _fail_perm
fail = _fail
done = _done
success = _success
