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
# @author: Matthew Story <matt.story@axialmarket.com>
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# TODO: signal handling for parent and child
# TODO: Concurrency?
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
        shout('{0} [-h|--help] [-v|--verbose] [-e|--env] [-E|--no-env]'\
              ' [-i|--ignore-down]', f)
        shout('        [-l|--lock] [-L|--no-lock]'\
              ' [-t ttl_seconds|--ttl=seconds]', f)
        shout('        [-m max_tries |--max-tries=int]'\
              ' [-S success_code|--success-code=int]', f)
        shout('        [-T fail_tmp_code|--fail-tmp-code=int]'\
              ' [-F fail_perm_code|--fail-perm-code=int] queue prog [args'\
              ' [...]]', f)
    sys.exit(exit)

# all fsq commands use a main function
def main(argv):
    global _PROG, _VERBOSE
    # defaults
    set_env = True
    no_open = False
    ignore_down = False

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'heEnilLt:m:S:T:F:', ( 'help',
                                   'env', 'no-env', 'no-open', 'ignore-down',
                                   'lock', 'no-lock', 'ttl=', 'max-tries=',
                                   'success-code=', 'fail-tmp-code=',
                                   'fail-perm-code=', ))
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
    if 2 > len(args):
        usage()

    try:
        items = fsq.scan(args[0], ignore_down=ignore_down, no_open=no_open)
    except fsq.FSQDownError:
        barf('{0} is down')
    except (fsq.FSQScanError, fsq.FSQPathError, ), e:
        barf(e.message)
    except fsq.FSQCoerceError, e:
        barf('cannot coerce queue; charset={0}'.format(_CHARSET))
    try:
        timefmt = fsq.const('FSQ_TIMEFMT')
        while True:
            try:
                item = items.next()
                # prepare to fork/exec
                try:
                    item_id = item.id.encode(_CHARSET)
                except UnicodeEncodeError, e:
                    barf('cannot coerce item id;'\
                         ' charset={0}'.format(_CHARSET))
                if set_env:
                    # set additional information in environment prior to fork
                    for env, attr in ( ( 'FSQ_ITEM_PID', 'pid', ),
                                       ( 'FSQ_ITEM_ENTROPY', 'entropy', ),
                                       ( 'FSQ_ITEM_HOSTNAME', 'hostname', ),
                                       ( 'FSQ_ITEM_ID', 'id', ), ):
                        try:
                            os.putenv(env,
                                      getattr(item, attr).encode(_CHARSET))
                        except UnicodeEncodeError, e:
                            barf('cannot coerce item {0};'
                                 ' charset={1}'.format(attr, _CHARSET))

                    # format tries and date to env
                    os.putenv('FSQ_ITEM_TRIES', str(item.tries))
                    try:
                        os.putenv('FSQ_ITEM_ENQUEUED_AT',
                                  item.enqueued_at.strftime(timefmt))
                    except ValueError:
                        barf('invalid timefmt: {0}'.format(timefmt))

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
                            barf('cannot dup: {0};'\
                                 ' aborting'.format(e.strerror))

                    # exec, potentially via PATH
                    try:
                        os.execvp(args[1], tuple(args[1:]) + item.arguments)
                    except ( OSError, IOError, ), e:
                        barf('{0}: cannot exec {0};'\
                             ' aborting'.format(e.strerror, args[1]))
                    except Exception, e:
                        barf('cannot execvp ({0}: {1});'\
                             ' aborting'.format(e.__class__.__name__,
                                                e.message))

                pid, rc = os.waitpid(pid, 0) # papa fork waits on baby fork
                if os.WIFEXITED(rc):
                    rc = os.WEXITSTATUS(rc)
                    try:
                        if fsq.const('FSQ_SUCCESS') == rc:
                            fsq.success(item)
                            chirp('{0}: succeeded'.format(item_id))
                        elif fsq.const('FSQ_FAIL_TMP') == rc:
                            fsq.fail_tmp(item)
                            shout('{0}: failed temporarily'.format(item_id))
                        else:
                            fsq.fail_perm(item)
                            shout('{0}: failed permanantly'.format(item_id))
                    except fsq.FSQEnqueueError, e:
                        barf(e.strerror.encode(_CHARSET))
                    except fsq.FSQError, e:
                        shout(e.strerror.encode(_CHARSET))
                #TODO: else ... was signalled, cleanup
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
        shout(dir(e))
        shout(e.message.encode(_CHARSET))

if __name__ == '__main__':
    main(sys.argv)
