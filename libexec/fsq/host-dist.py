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

    if 1 == len(args):
        all_hosts = True
        hosts = None
    else:
        hosts = args[1:]

    fsq.fork_exec_items(args[0], ignore_down=ignore_down, host=all_hosts,
                        no_open=no_open, hosts=hosts if hosts else None,
                        no_done=no_done, verbose=_VERBOSE, link=link)
    if trigger:
        fsq.host_trigger_pull(args[0])

if __name__ == '__main__':
    main(sys.argv)
