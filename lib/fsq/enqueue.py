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
              FSQ_ITEM_MODE, FSQ_ENQUEUE_MAX_TRIES, path as fsq_path, construct
from .internal import coerce_unicode, uid_gid, rationalize_file,\
                      wrap_io_os_err

####### INTERNAL MODULE FUNCTIONS AND ATTRIBUTES #######
# these keyword arguments are supported, but don't have defaults
# they are just passed along to _standard_args, having this argument
# list repeated in 2 places is non-ideal
_STANDARD_KEYS = ('entropy', 'tries', 'pid', 'now', 'hostname',)

# get the standard arguments that we always send
def _std_args(entropy=0, tries=0, pid=None, timefmt=FSQ_TIMEFMT,
                   now=None, hostname=socket.gethostname()):
    '''Provide the arguments which are always required by FSQ spec for
       uniqueness time-based ordering and environment, returns a list:

           [
               now,      # formatted by timefmt (default FSQ_TIMEFMT)
               entropy,  # for uniqueness, (default 0)
               pid,      # default is pid of the calling process
               hostname, # default is this machine's hostname
               tries,    # number of times this work has been attempted
           ]             # (default 0)
    '''
    now = datetime.datetime.now() if now is None else now
    pid = os.getpid() if pid is None else pid
    try:
        fmt_time = now.strftime(timefmt)

    except AttributeError, e:
        raise TypeError(u'now must be a datetime, date, time, or other type'\
                        u' supporting strftime, not {0}'.format(
                        now.__class__.__name__))
    except TypeError, e:
        raise TypeError(u'timefmt must be a string or read-only buffer,'\
                        ' not {0}'.format(timefmt.__class__.__name__))
    except ValueError, e:
        raise FSQTimeFmtError(errno.EINVAL, u'invalid fmt for strftime:'\
                              ' {0}'.format(timefmt))
    return [ coerce_unicode(fmt_time), coerce_unicode(entropy),
             coerce_unicode(pid), coerce_unicode(hostname),
             coerce_unicode(tries) ]

# TODO: provide an internal/external streamable queue item object use that
#       instead of this for the enqueue family of functions
# make a queue item from args, return a file
def _mkitem(trg_path, args, user=FSQ_ITEM_USER, group=FSQ_ITEM_GROUP,
            mode=FSQ_ITEM_MODE, entropy=None,
            enqueue_max_tries=FSQ_ENQUEUE_MAX_TRIES, delimiter=FSQ_DELIMITER,
            encodeseq=FSQ_ENCODE, dry_run=False, **std_kwargs):
    flags = os.O_WRONLY
    if not dry_run:
        flags |= os.O_CREAT|os.O_EXCL
    trg_fd = trg = name = None
    tried = 0
    recv_entropy = True if std_kwargs.has_key('entropy') else False
    now, entropy, pid, host, tries = _std_args(**std_kwargs)
    # try a few times
    while 0 >= enqueue_max_tries or enqueue_max_tries > tried:
        tried += 1
        # get low, so we can use some handy options; man 2 open
        try:
            name = construct((now, entropy, pid, host, tries, ) + tuple(args),
                             delimiter=delimiter, encodeseq=encodeseq)
            trg = os.path.join(trg_path, name)
            # TODO: for dry run, a stat is more efficient than open
            trg_fd = os.open(trg, flags, mode)
        except (OSError, IOError, ), e:
            # if file already exists, retry or break
            if not dry_run and e.errno == errno.EEXIST:
                if recv_entropy:
                    break
                entropy = tried
                continue
            # ENOENT is success for dry-run
            elif dry_run and e.errno == errno.ENOENT:
                return trg, None
            raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
        try:
            # if we opened the file successfully on dry_run, we failed
            if dry_run:
                if recv_entropy:
                    break
                entropy = tried
                continue
            # if we've succeeded
            else:
                try:
                    if user is not None or group is not None:
                        # set user/group ownership for file; man 2 fchown
                        os.fchown(trg_fd, *uid_gid(user, group, fd=trg_fd))
                    # return something that is safe to close in scope
                    return trg, os.fdopen(os.dup(trg_fd), 'wb', 1)
                except (OSError, IOError, ), e:
                    os.unlink(trg)
                    raise FSQEnqueueError(e.errno, wrap_io_os_err(e))
        # we return a file on a dup'ed fd, always close original fd
        finally:
            os.close(trg_fd)

    # if we got nowhere ... raise
    raise FSQEnqueueMaxTriesError(errno.EAGAIN, u'max tries exhausted for:'\
                                  u' {0}'.format(trg))

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
    # grab only the kwargs we want for _mkitem
    std_kwargs = {}
    for k in _STANDARD_KEYS:
        try:
            std_kwargs[k] = kwargs[k]
            del kwargs[k]
        except KeyError:
            pass
    if kwargs.keys():
        raise TypeError(u'venqueue() got an unexpected keyword argument:'\
                        u' {0}'.format(kwargs.keys()[0]))
    # open source file
    with closing(rationalize_file(item_f)) as src_file:
        tmp_path = fsq_path.tmp(trg_queue, root=root, tmp=tmp)
        queue_path = fsq_path.queue(trg_queue, root=root, queue=queue)
        # yeild temporary queue item
        name, trg_file = _mkitem(tmp_path, args, user=user, group=group,
                                 mode=mode, delimiter=delimiter,
                                 encodeseq=encodeseq, **std_kwargs)
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

                # rename will overwrite trg, so test existence here
                # there is a slight race-condition here ...
                commit_name, discard = _mkitem(queue_path, args,
                                               dry_run=True, **std_kwargs)
                os.rename(name, commit_name)

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
            finally:
                pass

def vsenqueue(trg_queue, item_s, args, **kwargs):
    '''Enqueue a string, or string-like object to queue with arbitrary
       arguments, vsenqueue is to venqueue what vsprintf is to vprintf,
       vsenqueue is to senqueue what vsprintf is to sprintf.
    '''
    return venqueue(trg_queue, StringIO(item_s), args, **kwargs)
