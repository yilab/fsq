#!/usr/bin/env python
# fsq-scan(1) -- a program for scanning an fsq queue, and executing programs
#                with item arguments and environments. should the executed
#                program exit FSQ_SUCCESS (default: 0), the queue item will be
#                marked ``done'', should the program exit FSQ_FAIL_TMP
#                (default: 111), the item will potentially be retried, should
#                the program exit FSQ_FAIL_PERM (default: 100), the item will
#                fail permanantly.  Any other exit code will denote permanant
#                failure.
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
# @author: Matthew Story <matt.story@axial.net>
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# TODO: Concurrency? -- not right now
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os

_PROG = "fsq-scan"
_VERBOSE = False
_CHARSET = fsq.const('FSQ_CHARSET')

def chirp(msg):
    if _VERBOSE:
        shout(msg)

def shout(msg, f=sys.stderr):
    '''Log to file (usually stderr), with progname: <log>'''
    print >> f, "{0}: {1}".format(_PROG, msg)
    f.flush()

def barf(msg, exit=None, f=sys.stderr):
    '''Exit with a log message (usually a fatal error)'''
    exit = fsq.const('FSQ_FAIL_TMP') if exit is None else exit
    shout(msg, f)
    sys.exit(exit)

def usage(asked_for=0):
    '''Exit with a usage string, used for bad argument or with -h'''
    exit =  fsq.const('FSQ_SUCCESS') if asked_for else\
                fsq.const('FSQ_FAIL_PERM')
    f = sys.stdout if asked_for else sys.stderr
    shout('{0} [opts] queue prog [args [...]]'.format(
          os.path.basename(_PROG)), f)
    if asked_for:
        shout('{0} [-h|--help] [-v|--verbose] [-e|--env]'\
              ' [-E|--no-env]'.format(os.path.basename(_PROG)), f)
        shout('        [-n|--no-open] [-i|--ignore-down]', f)
        shout('        [-k|--empty-ok] [-D|--no-done]', f)
        shout('        [-l|--lock] [-L|--no-lock]', f)
        shout('        [-t ttl_seconds|--ttl=seconds]', f)
        shout('        [-m max_tries|--max-tries=int]', f)
        shout('        [-S success_code|--success-code=int]', f)
        shout('        [-T fail_tmp_code|--fail-tmp-code=int]', f)
        shout('        [-F fail_perm_code|--fail-perm-code=int]', f)
        shout('        queue prog [args [...]]', f)
    sys.exit(exit)

def done_item(item, code):
    '''Succeed or fail an item based on the return code of a program'''
    try:
        if fsq.const('FSQ_SUCCESS') == code:
            fsq.success(item)
            chirp('{0}: succeeded'.format(item.id))
        elif fsq.const('FSQ_FAIL_TMP') == code:
            fsq.fail_tmp(item)
            shout('{0}: failed temporarily'.format(item.id))
        else:
            fsq.fail_perm(item)
            shout('{0}: failed permanantly'.format(item.id))
    except fsq.FSQEnqueueError, e:
        shout(e.strerror.encode(_CHARSET))
        return -1
    except fsq.FSQError, e:
        shout(e.strerror.encode(_CHARSET))
    return 0

def setenv(item, timefmt):
    '''Set environment, based on item.  Usually done in a baby fork'''
    for env, att in (( 'FSQ_ITEM_PID', 'pid', ),
                     ( 'FSQ_ITEM_ENTROPY', 'entropy', ),
                     ( 'FSQ_ITEM_HOSTNAME', 'hostname', ),
                     ( 'FSQ_ITEM_ID', 'id', ), ):
        try:
            os.putenv(env, getattr(item,
                      att).encode(_CHARSET))
        except UnicodeEncodeError:
            shout('cannot coerce item {0};'
                  ' charset={1}'.format(att, _CHARSET))
            return -1

    # format tries and date to env
    os.putenv('FSQ_ITEM_TRIES', str(item.tries))
    try:
        os.putenv('FSQ_ITEM_ENQUEUED_AT',
                  item.enqueued_at.strftime(timefmt))
    except ValueError:
        shout('invalid timefmt: {0}'.format(timefmt))
        return -1
    return 0


# all fsq commands use a main function
def main(argv):
    global _PROG, _VERBOSE
    # defaults
    set_env = True
    no_open = False
    ignore_down = False
    empty_ok = False
    no_done = False
    main_rc = 0

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'hveEnilLkDt:m:S:T:F:', ( 'help',
                                   'env', 'no-env', 'no-open', 'ignore-down',
                                   'lock', 'no-lock', 'empty-ok', 'no-done',
                                   'ttl=', 'max-tries=', 'success-code=',
                                   'fail-tmp-code=', 'fail-perm-code=',
                                   'verbose', ))
    except getopt.GetoptError, e:
        barf('invalid flag: -{0}{1}'.format('-' if 1 < len(e.opt) else '',
             e.opt))
    try:
        for flag, opt in opts:
            if '-v' == flag or '--verbose' == flag:
                _VERBOSE = True
            elif '-e' == flag or '--env' == flag:
                set_env = True
            elif '-E' == flag or '--no-env' == flag:
                set_env = False
            elif '-n' == flag or '--no-open' == flag:
                no_open = True
            elif '-i' == flag or '--ignore-down' == flag:
                ignore_down = True
            elif '-l' == flag or '--lock' == flag:
                fsq.set_const('FSQ_LOCK', True)
            elif '-L' == flag or '--no-lock' == flag:
                fsq.set_const('FSQ_LOCK', False)
            elif '-k' == flag or '--empty-ok' == flag:
                empty_ok = True
            elif '-D' == flag or '--no-done' == flag:
                no_done = True
            elif '-t' == flag or '--ttl' == flag:
                fsq.set_const('FSQ_TTL', opt)
            elif '-m' == flag or '--max-tries' == flag:
                fsq.set_const('FSQ_MAX_TRIES', opt)
            elif '-S' == flag or '--success-code' == flag:
                fsq.set_const('FSQ_SUCCESS', opt)
            elif '-T' == flag or '--fail-tmp-code' == flag:
                fsq.set_const('FSQ_FAIL_TMP', opt)
            elif '-F' == flag or '--fail-perm-code' == flag:
                fsq.set_const('FSQ_FAIL_PERM', opt)
            elif '-h' == flag or '--help' == flag:
                usage(1)
    except ( fsq.FSQEnvError, fsq.FSQCoerceError, ):
        barf('invalid argument for flag: {0}'.format(flag))

    # validate args
    num_required = 1 if empty_ok else 2
    if num_required > len(args):
        usage()

    try:
        items = fsq.scan(args[0], ignore_down=ignore_down, no_open=no_open)
    except fsq.FSQDownError:
        barf('{0} is down')
    except (fsq.FSQScanError, fsq.FSQPathError, ), e:
        barf(e.strerror)
    except fsq.FSQCoerceError, e:
        barf('cannot coerce queue; charset={0}'.format(_CHARSET))
    try:
        fail_perm = fsq.const('FSQ_FAIL_PERM')
        fail_tmp = fsq.const('FSQ_FAIL_PERM')
        success = fsq.const('FSQ_SUCCESS')
        timefmt = fsq.const('FSQ_TIMEFMT')
        while True:
            try:
                item = items.next()
                exec_args = tuple(args[1:]) + item.arguments
                # cannot exec nothing
                if empty_ok and 0 == len(exec_args):
                    shout('cannot execvp empty arguments with empty_ok;'\
                          ' failing tmp')
                    if not no_done and -1 == done_item(item, fail_perm):
                        sys.exit(fail_tmp)
                    continue

                # prepare to fork/exec
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
                    # exec, potentially via PATH
                    try:
                        os.execvp(exec_args[0], exec_args)
                    except ( OSError, IOError, ), e:
                        shout('{0}: cannot exec {0}'.format(e.strerror,
                              args[0]))
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
                        if not no_done and -1 == done_item(item, os.WEXITSTATUS(rc)):
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

            except fsq.FSQError, e:
                shout(e.strerror.encode(_CHARSET))
            except StopIteration:
                break
            finally:
                try:
                    del item
                except NameError:
                    pass

    except fsq.FSQDownError:
        barf('{0} is down'.format(args[0]))
    except fsq.FSQError, e:
        shout(e.strerror.encode(_CHARSET))

if __name__ == '__main__':
    main(sys.argv)
