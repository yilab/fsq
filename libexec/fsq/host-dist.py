#!/usr/bin/env python
# fsq-host-dist(1) -- a program for distributing queues to host queues
#
# @author: Jeff Rand <jeff.rand@axial.net>
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os

_PROG = "fsq-host-dist"
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
    shout('{0} [opts] queue host [host [...]]'.format(
          os.path.basename(_PROG)), f)
    if asked_for:
        shout('{0} [-h|--help] [-v|--verbose] [-I|--link]'.format(
                                    os.path.basename(_PROG)), f)
        shout('        [-g|--trigger]', f)
        shout('        [-n|--no-open] [-i|--ignore-down]', f)
        shout('        [-l|--lock] [-L|--no-lock]', f)
        shout('        [-t ttl_seconds|--ttl=seconds]', f)
        shout('        [-m max_tries|--max-tries=int]', f)
        shout('        [-S success_code|--success-code=int]', f)
        shout('        [-T fail_tmp_code|--fail-tmp-code=int]', f)
        shout('        [-F fail_perm_code|--fail-perm-code=int]', f)
        shout('        queue host [host [...]]', f)

    return exit

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

def main(argv):
    global _PROG, _VERBOSE
    link = False
    trigger = False
    flag = None
    all_hosts = False
    no_open = False
    ignore_down = False
    no_done = False
    main_rc = 0

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'hvnilLDIgt:m:S:T:F:', ( 'help',
                                   'no-open', 'ignore-down',
                                   'lock', 'no-lock', 'no-done',
                                   'link', 'trigger', 'ttl=', 'max-tries=',
                                   'success-code=', 'fail-tmp-code=',
                                   'fail-perm-code=', 'verbose',  ))
        for flag, opt in opts:
            if flag in ( '-v', '--verbose', ):
                _VERBOSE = True
            elif flag in ( '-I', '--link', ):
                link = True
            elif flag in ( '-g', '--trigger', ):
                trigger = True
            elif '-n' == flag or '--no-open' == flag:
                no_open = True
            elif '-i' == flag or '--ignore-down' == flag:
                ignore_down = True
            elif '-l' == flag or '--lock' == flag:
                fsq.set_const('FSQ_LOCK', True)
            elif '-L' == flag or '--no-lock' == flag:
                fsq.set_const('FSQ_LOCK', False)
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
            elif flag in ( '-h', '--help', ):
                return usage(1)
    except ( fsq.FSQEnvError, fsq.FSQCoerceError, ):
        barf('invalid argument for flag: {0}'.format(flag))

    if 0 == len(args):
        return usage()

    queue = args[0]

    if 1 == len(args):
        all_hosts = True
        hosts = None
    else:
        hosts = args[1:]

    try:
        items = fsq.scan(queue, ignore_down=ignore_down, no_open=no_open,
                         hosts=hosts)
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
        while True:
            try:
                item = items.next()

                try:
                    item_id = item.id.encode(_CHARSET)
                except UnicodeEncodeError, e:
                    barf('cannot coerce item id;'\
                         ' charset={0}'.format(_CHARSET))
                chirp('working on distributing {0} ...'.format(item_id))
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
                    # exec, potentially via PATH
                    try:
                        chirp(fsq.reenqueue(item, queue, hosts=hosts,
                                      all_hosts=all_hosts, link=link))
                        os._exit(0)
                    except ( fsq.FSQReenqueueError ), e:
                        shout('{0}: cannot reenqueue {0}'.format(e.strerror,
                              item_id))
                        os._exit(fail_tmp)
                    except Exception, e:
                        shout('cannot reenqueue ({0}: {1})'.format(
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

            except fsq.FSQError, e:
                shout(e.strerror.encode(_CHARSET))
            except StopIteration:
                break
            finally:
                try:
                    del item
                except NameError:
                    pass
        if trigger:
            fsq.host_trigger_pull(queue)
    except fsq.FSQDownError:
        barf('{0} is down'.format(args[0]))
    except fsq.FSQError, e:
        shout(e.strerror.encode(_CHARSET))
    except ( fsq.FSQEnvError, fsq.FSQCoerceError, ):
        shout('invalid argument for flag: {0}'.format(flag))
        return fsq.const('FSQ_FAIL_PERM')
    except fsq.FSQInstallError, e:
        shout(e.strerror)
        return fsq.const('FSQ_FAIL_TMP')
    except getopt.GetoptError, e:
        shout('invalid flag: -{0}{1}'.format('-' if 1 < len(e.opt) else '',
              e.opt))
        return fsq.const('FSQ_FAIL_TMP')

if __name__ == '__main__':
    main(sys.argv)
