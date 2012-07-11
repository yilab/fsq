# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axialmarket.com>
#
# fsq/enqueue.py -- provides enqueueing functions: enqueue, senqueue,
#                   venqueue, vsenqueue
#
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
# This software is for POSIX compliant systems only.
import errno
import os
import socket
import datetime
from cStringIO import StringIO
from contextlib import closing

from . import FSQInternalError, FSQTimeFmtError, FSQEnqueueError,\
              FSQEnqueueMaxTriesError, FSQ_DELIMITER, FSQ_TIMEFMT, FSQ_QUEUE,\
              FSQ_TMP, FSQ_ROOT, FSQ_ENCODE, FSQ_ITEM_USER, FSQ_ITEM_GROUP,\
              FSQ_ITEM_MODE, FSQ_ENQUEUE_MAX_TRIES, path as fsq_path, mkitem
from .internal import coerce_unicode, uid_gid, rationalize_file,\
                      wrap_io_os_err

# TODO: provide an internal/external streamable queue item object use that
#       instead of this for the enqueue family of functions
#       make a queue item from args, return a file

####### EXPOSED METHODS #######
def enqueue(trg_queue, item_f, *args, **kwargs):
    '''Enqueue the contents of a file, or file-like object, file-descriptor or
       the contents of a file at an address (e.g. '/my/file') queue with
       arbitrary arguments, enqueue is to venqueue what printf is to vprintf
    '''
    return venqueue(trg_queue, item_f, args, **kwargs)

def senqueue(trg_queue, item_s, *args, **kwargs):
    '''Enqueue a string, or string-like object to queue with arbitrary
       arguments, senqueue is to enqueue what sprintf is to printf, senqueue
       is to vsenqueue what sprintf is to vsprintf.
    '''
    return vsenqueue(trg_queue, item_s, args, **kwargs)

def venqueue(trg_queue, item_f, args, delimiter=FSQ_DELIMITER,
             encodeseq=FSQ_ENCODE, timefmt=FSQ_TIMEFMT, queue=FSQ_QUEUE,
             tmp=FSQ_TMP, root=FSQ_ROOT, user=FSQ_ITEM_USER,
             group=FSQ_ITEM_GROUP, mode=FSQ_ITEM_MODE,
             enqueue_max_tries=FSQ_ENQUEUE_MAX_TRIES, **kwargs):
    '''Enqueue the contents of a file, or file-like object, file-descriptor or
       the contents of a file at an address (e.g. '/my/file') queue with
       an argument list, venqueue is to enqueue what vprintf is to printf

       If entropy is passed in, failure on duplicates is raised to the caller,
       if entropy is not passed in, venqueue will increment entropy until it
       can create the queue item.
    '''
    # open source file
    with closing(rationalize_file(item_f)) as src_file:
        tmp_path = fsq_path.tmp(trg_queue, root=root, tmp=tmp)
        queue_path = fsq_path.queue(trg_queue, root=root, queue=queue)
        # yeild temporary queue item
        name, trg_file = mkitem(tmp_path, args, user=user, group=group,
                                mode=mode, delimiter=delimiter,
                                encodeseq=encodeseq,
                                enqueue_max_tries=enqueue_max_tries,
                                **kwargs)
        # tmp target file
        with closing(trg_file):
            try:
                # i/o time ... assume line-buffered
                while True:
                    line = src_file.readline()
                    if not line:
                        break
                    trg_file.write(line)
                # flush buffers, and force write to disk pre mv.
                trg_file.flush()
                os.fsync(trg_file.fileno())

                # hard-link into queue, unlink tmp, failure case here leaves
                # cruft in tmp, but no race condition into queue
                commit_name, dis = mkitem(queue_path, args, link_src=name,
                                         encodeseq=encodeseq,
                                         enqueue_max_tries=enqueue_max_tries,
                                         **kwargs)
                os.unlink(name)

                # return the queue item id (filename)
                return os.path.basename(commit_name)
            except Exception, e:
                try:
                    os.unlink(name)
                except OSError, e:
                    if e.errno != errno.ENOENT:
                       raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
                if isinstance(e, OSError) or isinstance(e, IOError):
                    raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
                raise e

def vsenqueue(trg_queue, item_s, args, **kwargs):
    '''Enqueue a string, or string-like object to queue with arbitrary
       arguments, vsenqueue is to venqueue what vsprintf is to vprintf,
       vsenqueue is to senqueue what vsprintf is to sprintf.
    '''
    return venqueue(trg_queue, StringIO(item_s), args, **kwargs)