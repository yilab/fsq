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
from . import FSQ_SUCCESS, FSQ_FAIL_TMP, FSQ_FAIL_PERM, FSQFailError,\
              FSQEnqueueMaxTriesError, FSQMaxTriesError, FSQTTLExpiredError,\
              path as fsq_path, mkitem
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
def fail_tmp(item, max_tries=None, ttl=None):
    '''Try to fail a work-item temporarily (up recount and keep in queue),
       if max tries or ttl is exhausted, escalate to permanant failure.'''
    try:
        max_tries = item.max_tries if max_tries is None else max_tries
        ttl = item.ttl if ttl is None else ttl

        # see if we need to fail perm
        check_ttl_max_tries(item.tries, item.enqueued_at, max_tries, ttl,
                            FSQ_FAIL_PERM)

        tries = item.tries + 1
        # construct path
        item_src = fsq_path.item(item.queue, item.id)
        # mv to tmp, then mv back into queue
        trg_path, discard = mkitem(fsq_path.tmp(item.queue), item.arguments,
                                   now=item.enqueued_at, pid=item.pid,
                                   tries=tries, link_src=item_src)
        _unlink(item_src)
        re_src, discard = mkitem(fsq_path.queue(item.queue), item.arguments,
                                 now=item.enqueued_at, pid=item.pid,
                                 tries=tries, link_src=trg_path)
        _unlink(trg_path)
        return os.path.basename(re_src)
    except AttributeError, e:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))
    except (FSQMaxTriesError, FSQTTLExpiredError,), e:
        fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'for item {0}; failed permanantly'.format(item.id),
        ])
        raise e
    except FSQEnqueueMaxTriesError, e:
        fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'cannot enqueue retry for item',
            u' {0}; failed permanantly'.format(item.id)
        ])
        raise e

def fail_perm(item):
    '''Fail a work-item permanatly by mv'ing it to queue's fail directory'''
    try:
        # The only thing we require to fail is an item_id and a queue
        # as an item may fail permanantly due to malformed item_id-ness
        arguments = getattr(item, 'arguments', [])
        now = getattr(item, 'enqueued_at', datetime.datetime.now())
        pid = getattr(item, 'pid', os.getpid())
        tries = getattr(item, 'tries', 0)
        item_id = item.id
        trg_queue = item.queue
    except AttributeError:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))

    # this methodology may result in items being in both fail and queue
    # but will guarentee uniqueness in the fail directory
    item_src = fsq_path.item(trg_queue, item_id)
    trg_path, discard = mkitem(fsq_path.fail(trg_queue), arguments, now=now,
                               pid=pid, tries=tries, link_src=item_src)
    _unlink(item_src)
    return os.path.basename(trg_path)

def done(item, done_type=None, max_tries=None, ttl=None):
    '''Wrapper for any type of finish, successful, permanant failure or
       temporary failure'''
    if done_type is None or done_type == FSQ_SUCCESS:
        return success(item)
    return fail(item, fail_type=done_type, max_tries=max_tries, ttl=ttl)

def fail(item, fail_type=None, max_tries=None, ttl=None):
    '''Fail a work item, either temporarily or permanantly'''
    # default to fail_perm
    if fail_type is not None and fail_type == FSQ_FAIL_TMP:
        return fail_tmp(item, max_tries=max_tries, ttl=ttl)
    return fail_perm(item)

def success(item):
    '''Successful finish'''
    try:
        # mv to done
        trg_queue = item.queue
        item_src = fsq_path.item(trg_queue, item.id)
        trg_path, discard = mkitem(fsq_path.done(trg_queue), item.arguments,
                                   now=item.enqueued_at, pid=item.pid,
                                   tries=item.tries, link_src=item_src)
        _unlink(item_src)
    except AttributeError, e:
        # DuckType TypeError'ing
        raise TypeError(u'item must be an FSQWorkItem, not:'\
                        u' {0}'.format(item.__class__.__name__))
    except FSQEnqueueMaxTriesError, e:
        fail_perm(item)
        e.message = u': '.join([
            e.message,
            u'cannot mark item completed',
            u' {0}; failed permanantly'.format(item.id)
        ])
        raise e

####### EXPOSED METHODS #######
def retry(*args, **kwargs):
    '''Retry is a convenience alias for fail_tmp'''
    return fail_tmp(*args, **kwargs)
