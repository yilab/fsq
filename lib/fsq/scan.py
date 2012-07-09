# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/constants.py -- a place for constants.  per FSQ specification,
#   constants take their value from the calling program environment
#   (if available), and default to the the expected values.
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
#   NB: changes to environment following first import, will not
#       affect values potentially a bug to clean up later.
#
# TODO: make the defaults build-time configurable
# This software is for POSIX compliant systems only.
import os
import errno

from . import FSQ_ROOT, FSQ_LOCK, FSQ_QUEUE, FSQ_DONE, FSQ_FAIL, FSQ_SUCCESS,\
              FSQ_FAIL_TMP, FSQ_FAIL_PERM, FSQ_TTL, FSQ_MAX_TRIES,\
              FSQ_TIMEFMT, FSQ_ENCODE, FSQWorkItem, path as fsq_path,\
              FSQScanError, FSQCannotLockError, FSQWorkItemError
from .internal import wrap_io_os_err

####### EXPOSED METHODS AND CLASSES #######
class FSQScanGenerator(object):
    '''FSQScanGenerator is a Generator object for yielding FSQWorkItems from a
       list of queue item ids, typcially passed in via the scan function.

       FSQScanGenerator is intended to be a minimalist object, capable of
       reverse engineering to a C-struct.  The C-struct will be similar to FTS
       (man 3 fts).
       BEWARE: If you choose not to lock, the item you are working on may be
       worked on by others, and may be moved (on failure or success) out from
       underneath you.  Should you send lock=False, it is assumed you are
       guarenteeing concurrency of 1 on the queue through some other
       mechanism.'''
    ####### MAGICAL METHODS AND ATTRS #######
    def __init__(self, trg_queue, item_ids, root=FSQ_ROOT, lock=FSQ_LOCK,
                 queue=FSQ_QUEUE, done=FSQ_DONE, fail=FSQ_FAIL,
                 success=FSQ_SUCCESS, fail_tmp=FSQ_FAIL_TMP,
                 fail_perm=FSQ_FAIL_PERM, ttl=FSQ_TTL,
                 max_tries=FSQ_MAX_TRIES, timefmt=FSQ_TIMEFMT,
                 encodeseq=FSQ_ENCODE):
        '''Construct an FSQScanGenerator object from a list of item_ids and a
           queue name.  The lock kwarg will override the default locking
           preference (taken from environment).'''
        # index of current item
        self._index = -1
        # current item
        self.item = None
        # list of item ids
        self.item_ids = item_ids
        self.queue = trg_queue
        self.done_dir = done
        self.fail_dir = fail
        self.queue_dir = queue
        self.root = root
        self.lock = lock
        self.fail_tmp = fail_tmp
        self.fail_perm = fail_perm
        self.success = success
        self.ttl = ttl
        self.max_tries = max_tries
        self.timefmt = timefmt

    def __iter__(self):
        return self

    def __del__(self):
        '''Always explicitely del the item to close a file if refcount = 0'''
        if hasattr(self, 'item'):
            del self.item

    def next(self):
        while self._index < len(self.item_ids)-1:
            self._index += 1
            # always destroy self.item to close file if necessary
            if getattr(self, 'item', None) is not None:
                del self.item
            try:
                self.item = FSQWorkItem(self.queue,
                                        self.item_ids[self._index],
                                        root=self.root, lock=self.lock,
                                        queue=self.queue_dir,
                                        done=self.done_dir,
                                        fail=self.fail_dir,
                                        success=self.success,
                                        fail_tmp=self.fail_tmp,
                                        fail_perm=self.fail_perm,
                                        ttl=self.ttl,
                                        max_tries=self.max_tries,
                                        timefmt=self.timefmt)
            except (FSQWorkItemError, FSQCannotLockError, ), e:
                # we discard on ENOENT -- e.g. something else already did the
                #  work
                # or EAGAIN -- e.g. cannot lock because something else is
                #  already doing the work
                if e.errno == errno.EAGAIN or e.errno == errno.ENOENT:
                    continue
                # else raise
                raise e
            return self.item

        if getattr(self, 'item', None) is not None:
            del self.item
        # if we break through loop with no exception, we're done
        raise StopIteration()

def scan(trg_queue, generator=FSQScanGenerator, root=FSQ_ROOT, lock=FSQ_LOCK,
         queue=FSQ_QUEUE, done=FSQ_DONE, fail=FSQ_FAIL, success=FSQ_SUCCESS,
         fail_tmp=FSQ_FAIL_TMP, fail_perm=FSQ_FAIL_PERM, ttl=FSQ_TTL,
         max_tries=FSQ_MAX_TRIES, timefmt=FSQ_TIMEFMT, encodeseq=FSQ_ENCODE):
    '''Given a queue, generate a list of files in that queue, and pass it to
       FSQScanGenerator for iteration.  The generator kwarg is provided here
       as a means of implementing a custom generator, use with caution.'''
    try:
        item_ids = os.listdir(fsq_path.queue(trg_queue, root=root,
                                             queue=queue))
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQScanError(e.errno, u'no such queue:'\
                               u' {0}'.format(trg_queue))
        raise FSQScanError(e.errno, wrap_io_os_err(e))

    # sort here should yield time then entropy sorted
    item_ids.sort()
    return generator(trg_queue, item_ids, root=FSQ_ROOT, lock=FSQ_LOCK,
                     queue=FSQ_QUEUE, done=FSQ_DONE, fail=FSQ_FAIL,
                     success=FSQ_SUCCESS, fail_tmp=FSQ_FAIL_TMP,
                     fail_perm=FSQ_FAIL_PERM, ttl=FSQ_TTL,
                     max_tries=FSQ_MAX_TRIES, timefmt=FSQ_TIMEFMT,
                     encodeseq=FSQ_ENCODE)
