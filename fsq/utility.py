# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Matthew Story <matt.story@axial.net>
# @author: Jeff Rand <jeff.rand@axial.net>
#
# fsq/utility.py -- a utility for fork/execing on queue items, to be used
#                   from the command line. should the executed
#                   program exit FSQ_SUCCESS (default: 0), the queue item will
#                   be marked ``done'', should the program exit FSQ_FAIL_TMP
#                   (default: 111), the item will potentially be retried,
#                   should the program exit FSQ_FAIL_PERM (default: 100),
#                   the item will fail permanantly. Any other exit code will
#                   denote permanant failure.
#
# WARNINGS:
#  * the --empty-ok flag potentially turns fsq-scan into an arbitrary
#      execution engine, use with caution
#  * without the --no-lock option, fsq-scan will LOCK_EX each item as it
#      iterates, should your exec'ed program hang, the file lock will not
#      be released.
#  * like xargs(1), if scan is terminated by signal, it orphans ... if a child
#      is terminated by signal, scan stops scanning.
#
# TODO: Concurrency? -- not right now
#
# This software is for POSIX compliant systems only.

import os
import sys
from . import scan, constants as _c, const, reenqueue, success, fail_tmp, \
              fail_perm, FSQScanError, FSQPathError, FSQCoerceError, \
              FSQDownError, FSQReenqueueError, FSQError, FSQInstallError, \
              FSQEnqueueError

_VERBOSE = False
_CHARSET = _c.FSQ_CHARSET

def chirp(msg):
    if _VERBOSE:
        shout(msg)

def shout(msg, f=sys.stderr):
    '''Log to file (usually stderr), with progname: <log>'''
    print >> f, "{0}".format(msg)
    f.flush()

def barf(msg, exit=None, f=sys.stderr):
    '''Exit with a log message (usually a fatal error)'''
    exit = const('FSQ_FAIL_TMP') if exit is None else exit
    shout(msg, f)
    sys.exit(exit)

def done_item(item, code):
    '''Succeed or fail an item based on the return code of a program'''
    try:
        if const('FSQ_SUCCESS') == code:
            success(item)
            chirp('{0}: succeeded'.format(item.id))
        elif const('FSQ_FAIL_TMP') == code:
            fail_tmp(item)
            shout('{0}: failed temporarily'.format(item.id))
        else:
            fail_perm(item)
            shout('{0}: failed permanantly'.format(item.id))
    except FSQEnqueueError, e:
        shout(e.strerror.encode(_CHARSET))
        return -1
    except FSQError, e:
        shout(e.strerror.encode(_CHARSET))
    return 0

def setenv(item, timefmt):
    '''Set environment, based on item.  Usually done in a baby fork'''
    for env, att in (( 'FSQ_ITEM_PID', 'pid', ),
                     ( 'FSQ_ITEM_ENTROPY', 'entropy', ),
                     ( 'FSQ_ITEM_HOSTNAME', 'hostname', ),
                     ( 'FSQ_ITEM_HOST', 'host', ),
                     ( 'FSQ_ITEM_ID', 'id', ), ):
        try:
            os.putenv(env, getattr(item,
                      att).encode(_CHARSET))
        except UnicodeEncodeError:
            shout('cannot coerce item {0};'
                  ' charset={1}'.format(att, _CHARSET))
            return -1
        except AttributeError:
            if att != 'host':
                raise

    # format tries and date to env
    os.putenv('FSQ_ITEM_TRIES', str(item.tries))
    try:
        os.putenv('FSQ_ITEM_ENQUEUED_AT',
                  item.enqueued_at.strftime(timefmt))
    except ValueError:
        shout('invalid timefmt: {0}'.format(timefmt))
        return -1
    return 0

def fork_exec_items(queue, ignore_down=False, no_open=False, host=False,
                    hosts=None, _CHARSET=_c.FSQ_CHARSET, no_done=False,
                    link=False, trigger=False, exec_args=None, set_env=True,
                    verbose=False, empty_ok=False):
    global _VERBOSE
    _VERBOSE = verbose
    main_rc = 0
    try:
        if exec_args:
            items = scan(queue, ignore_down=ignore_down, no_open=no_open,
                         host=host, hosts=hosts)
        else:
            items = scan(queue, ignore_down=ignore_down, no_open=no_open)
    except FSQDownError:
        barf('{0} is down')
    except (FSQScanError, FSQPathError, ), e:
        barf(e.strerror)
    except FSQCoerceError, e:
        barf('cannot coerce queue; charset={0}'.format(_CHARSET))
    try:
        fail_perm = const('FSQ_FAIL_PERM')
        fail_tmp = const('FSQ_FAIL_PERM')
        success = const('FSQ_SUCCESS')
        timefmt = const('FSQ_TIMEFMT')
        while True:
            try:
                item = items.next()
                # cannot exec nothing
                if empty_ok and 0 == len(exec_args):
                    shout('cannot execvp empty arguments with empty_ok;'\
                          ' failing tmp')
                    if not no_done and -1 == done_item(item, fail_perm):
                        sys.exit(fail_tmp)
                    continue
                try:
                    item_id = item.id.encode(_CHARSET)
                except UnicodeEncodeError, e:
                    barf('cannot coerce item id;'\
                         ' charset={0}'.format(_CHARSET))
                chirp('working on {0} ...'.format(item_id))
                try:
                    pid = os.fork()
                except Exception, e:
                    barf("cannot fork; aborting")

                if 0 == pid: # child fork
                    if not no_open:
                        try:
                            # if available, open item for reading on stdin
                            os.dup2(item.item.fileno(), sys.stdin.fileno())
                        except ( OSError, IOError, ), e:
                            barf('cannot dup: {0}'.format(e.strerror))
                    # setup the environment -- so C-style it hurts
                    if set_env and -1 == setenv(item, timefmt):
                        os._exit(fail_tmp)
                    if not exec_args:
                        # exec, potentially via PATH
                        try:
                            chirp(reenqueue(item, queue, hosts=hosts,
                                            all_hosts=host, link=link))
                            os._exit(0)
                        except ( FSQReenqueueError ), e:
                            shout('{0}: cannot reenqueue {0}'.format(e.strerror,
                                  item_id))
                            os._exit(fail_tmp)
                        except Exception, e:
                            shout('cannot reenqueue ({0}: {1})'.format(
                                  e.__class__.__name__, e.message))
                            os._exit(fail_tmp)
                    else:
                        try:
                            os.execvp(exec_args[0], exec_args + item.arguments)
                        except ( OSError, IOError, ), e:
                            shout('{0}: cannot exec {0}'.format(e.strerror,
                                  queue))
                            os._exit(fail_tmp)
                        except Exception, e:
                            shout('cannot execvp ({0}: {1})'.format(
                                  e.__class__.__name__, e.message))
                            os._exit(fail_tmp)
                    ######### NOT REACHED
                    os._exit(fail_perm)
                else: # if pid is non-0, we are the parent fork
                    pid, rc = os.waitpid(pid, 0) # wait on baby fork
                    if os.WIFEXITED(rc):
                        if not no_done and\
                            -1 == done_item(item, os.WEXITSTATUS(rc)):
                            sys.exit(fail_tmp)
                        if rc == fail_perm:
                            main_rc = rc
                        elif main_rc != fail_perm and rc != success:
                            main_rc = rc
                    else:
                        if not no_done and -1 == done_item(item, fail_perm):
                            sys.exit(fail_tmp)
                        barf('{0}: processing terminated by signal {1};'\
                             ' aborting'.format(item_id, os.WTERMSIG(rc)))
            except FSQError, e:
                shout(e.strerror.encode(_CHARSET))
            except StopIteration:
                break
            finally:
                try:
                    del item
                except NameError:
                    pass
    except FSQDownError:
        barf('{0} is down'.format(queue))
    except FSQError, e:
        shout(e.strerror.encode(_CHARSET))
    except FSQInstallError, e:
        shout(e.strerror)
        return const('FSQ_FAIL_TMP')

