# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
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

from . import constants as _c, FSQWorkItem, path as fsq_path, FSQScanError,\
              FSQCannotLockError, FSQWorkItemError, FSQDownError, FSQError,\
              is_down, hosts as fsq_hosts, host_is_down
from .internal import wrap_io_os_err

####### EXPOSED METHODS AND CLASSES #######
class FSQScanGenerator(object):
    '''FSQScanGenerator is a Generator object for yielding FSQWorkItems from a
       list of queue item ids, typcially passed in via the scan function.

       Should a queue item be exclusively locked by another operation,
       FSQScanGenerator will quietly skip the item; FSQScanGenerator will also
       quietly skip items that no longer exist, assuming that these items have
       been completed by other processes.

       FSQScanGenerator will respect down-files, before each item is
       dispatched, FSQScanGenerator will stat the down-file, to verify that
       the queue has not gone down.  Should the queue be down,
       FSQScanGenerator will raise FSQDownError. Should you want to ignore
       down-files, pass in None or an empty string as the kwarg ``down'', this
       functionality is useful for introspecting down'ed queues.

       FSQScanGenerator is intended to be a minimalist object, capable of
       reverse engineering to a C-struct.  The C-struct will be similar to FTS
       (man 3 fts).

       BEWARE: If you choose not to lock, the item you are working on may be
       worked on by others, and may be moved (on failure or success) out from
       underneath you.  Should you send lock=False, it is assumed you are
       guarenteeing concurrency of 1 on the queue through some other
       mechanism.'''
    ####### MAGICAL METHODS AND ATTRS #######
    def __init__(self, queue, item_ids, lock=None, ttl=None,
                 max_tries=None, ignore_down=False, no_open=False):
        '''Construct an FSQScanGenerator object from a list of item_ids and a
           queue name.  The lock kwarg will override the default locking
           preference (taken from environment).'''
        # index of current item
        self._index = -1

        # current item
        self.item = None
        self.queue = queue

        # list of item ids
        self.item_ids = item_ids
        self.lock = _c.FSQ_LOCK if lock is None else lock
        self.ttl = _c.FSQ_TTL if ttl is None else ttl
        self.max_tries = _c.FSQ_MAX_TRIES if max_tries is None else max_tries
        self.ignore_down = ignore_down
        self.no_open = no_open

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
                host = self.item_ids[self._index][0]
                item = self.item_ids[self._index][1]
            except TypeError:
                host = None
                item = self.item_ids[self._index]
            if self.ignore_down or is_down(self.queue, host=host):
                raise FSQDownError(errno.EAGAIN, u'queue {0}: is'\
                                   u' down'.format(self.queue))
            try:
                self.item = FSQWorkItem(self.queue,
                                        item,
                                        lock=self.lock, ttl=self.ttl,
                                        max_tries=self.max_tries,
                                        no_open=self.no_open,
                                        host=host)
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

def scan(queue, lock=None, ttl=None, max_tries=None, ignore_down=False,
         no_open=False, generator=FSQScanGenerator, host=False, hosts=None):
    '''Given a queue, generate a list of files in that queue, and pass it to
       FSQScanGenerator for iteration.  The generator kwarg is provided here
       as a means of implementing a custom generator, use with caution.'''
    lock = _c.FSQ_LOCK if lock is None else lock
    ttl = _c.FSQ_TTL if lock is None else ttl
    max_tries = _c.FSQ_MAX_TRIES if max_tries is None else max_tries
    item_ids = []
    try:
        if not host and not hosts:
            item_ids = os.listdir(fsq_path.queue(queue))
        else:
            if not hosts:
                hosts = fsq_hosts(queue)
            for host in hosts:
                if not host_is_down(queue, host):
                    for item in os.listdir(fsq_path.queue(queue, host)):
                        item_ids.append((host, item))
    except (OSError, IOError, ), e:
        if e.errno == errno.ENOENT:
            raise FSQScanError(e.errno, u'no such queue:'\
                               u' {0}'.format(queue))
        elif isinstance(e, FSQError):
            raise e
        raise FSQScanError(e.errno, wrap_io_os_err(e))

    # sort here should yield time then entropy sorted
    item_ids.sort()
    return generator(queue, item_ids, lock=lock, ttl=ttl, max_tries=max_tries,
                     no_open=no_open)
