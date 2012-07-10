# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/items.py -- provides items classes for fsq: FSQItem, FSQEnqueueItem
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import errno
import datetime

from . import FSQ_ROOT, FSQ_LOCK, FSQ_QUEUE, FSQ_DONE, FSQ_FAIL, FSQ_SUCCESS,\
              FSQ_FAIL_TMP, FSQ_FAIL_PERM, FSQ_TTL, FSQ_MAX_TRIES,\
              FSQ_TIMEFMT, FSQ_ENCODE, path as fsq_path, deconstruct,\
              FSQMalformedEntryError, FSQTimeFmtError, FSQWorkItemError#,\
              #fail as fsq_fail, success as fsq_success
from .internal import rationalize_file, wrap_io_os_err

class FSQEnqueueItem(object):
    pass

class FSQWorkItem(object):
    '''An FSQWorkItem object.  FSQItem stores an open and potentially
       exclusive-locked file to a work file as the attribute self.file, opened
       in read-only mode.

       FSQWorkItem is intended to a minimalist object, capable of reverse
       engineering to a C struct.  The C struct will support all attributes,
       but the methods will not be available, they will be available as
       include level functions taking a *WorkItem struct as their first
       argument.

       BEWARE: If you choose not to lock, the item you are working on may be
       worked on by others, and may be moved (on failure or success) out from
       underneath you.  Should you send lock=False, it is assumed you are
       guarenteeing concurrency of 1 on the queue through some other
       mechanism.'''
    ####### MAGICAL METHODS AND ATTRS #######
    def __init__(self, trg_queue, item_id, root=FSQ_ROOT, lock=FSQ_LOCK,
                 queue=FSQ_QUEUE, done=FSQ_DONE, fail=FSQ_FAIL,
                 success=FSQ_SUCCESS, fail_tmp=FSQ_FAIL_TMP,
                 fail_perm=FSQ_FAIL_PERM, ttl=FSQ_TTL,
                 max_tries=FSQ_MAX_TRIES, timefmt=FSQ_TIMEFMT,
                 encodeseq=FSQ_ENCODE):
        '''Construct an FSQWorkItem object from an item_id (file-name), and
           queue-name.  The lock kwarg will override the default locking
           preference (taken from environment).'''
        # open file immediately
        try:
            self.file = rationalize_file(fsq_path.item(trg_queue, item_id,
                                         root=root, queue=queue), lock=lock)
        except (OSError, IOError, ), e:
            if e.errno == errno.ENOENT:
                raise FSQWorkItemError(e.errno, u'no such item in queue {0}:'\
                                       u' {1}'.format(trg_queue, item_id))
            raise FSQWorkItemError(e.errno, wrap_io_os_err(e))
        try:
            self.queue = trg_queue
            self.done_dir = done
            self.fail_dir = fail
            self.queue_dir = queue
            self.id = item_id
            self.root = root
            self.lock = lock
            self.fail_tmp = fail_tmp
            self.fail_perm = fail_perm
            self.success = success
            self.ttl = ttl
            self.max_tries = max_tries
            self.timefmt = timefmt
            self.delimiter, arguments = deconstruct(item_id,
                                                    encodeseq=encodeseq)
            try:
                # construct datetime.datetime from enqueued_at
                self.enqueued_at = datetime.datetime.strptime(arguments[0],
                                                              timefmt)
                self.entropy = arguments[1]
                self.pid = arguments[2]
                self.hostname = arguments[3]
                self.tries = arguments[4]
                self.arguments = tuple(arguments[5:])
            except IndexError, e:
                raise FSQMalformedEntryError(fail_perm, u'needed at least 4'\
                                             u' arguments to unpack, got:'\
                                             u' {0}'.format(len(arguments)))
            except ValueError, e:
                raise FSQTimeFmtError(fail_perm, u'invalid date string for'\
                                      u' strptime fmt {0}:'\
                                      u' {1}'.format(timefmt, enqueued_at))
        except Exception, e:
            try:
                fail_type = getattr(e, 'errno', fail_perm)
                #self.fail(fail_type)
            finally:
                self.file.close()
            raise e

    def __del__(self):
        '''Always close the file when the ref count drops to 0'''
        if hasattr(self, 'file'):
            self.file.close()

    ####### EXPOSED METHODS AND ATTRS #######
    #def fail(self, fail_type=None):
    #    '''Fail this item either temporarily or permanantly.  This function
    #       may be called mid setup, so it takes pain to ensure that we always
    #       have values to send to the fail function, even if those values have
    #       not been initialized on self.'''
    #    if fail_type is None:
    #        fail_type = getattr(self, 'fail_type', FSQ_FAIL_PERM)
    #    fsq_fail(self, fail_type=fail_type,
    #             fail=getattr(self, 'fail_dir', FSQ_FAIL),
    #             fail_tmp=getattr(self, 'fail_tmp', FSQ_FAIL_TMP),
    #             fail_perm=getattr(self, 'fail_perm', FSQ_FAIL_PERM),
    #             max_tries=getattr(self, 'max_tries', FSQ_MAX_TRIES),
    #             ttl=getattr(self, 'ttl', FSQ_TTL))
