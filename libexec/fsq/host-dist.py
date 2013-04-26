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

def usage(asked_for=0):
    '''Exit with a usage string, used for bad argument or with -h'''
    exit =  fsq.const('FSQ_SUCCESS') if asked_for else\
                fsq.const('FSQ_FAIL_PERM')
    f = sys.stdout if asked_for else sys.stderr
    shout('{0} [opts] queue prog [args [...]]'.format(
          os.path.basename(_PROG)), f)
    if asked_for:
        shout('{0} [-h|--help] [-v|--verbose] [-l|--link]'.format(
              os.path.basename(_PROG)), f)
        shout('        [-t|--trigger]', f)
        shout('        queue host [host [...]]', f)
    return 0 if asked_for else fsq.const('FSQ_FAIL_PERM')

def main(argv):
    global _PROG, _VERBOSE
    link = False
    trigger = False
    flag = None
    all_hosts = False

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'hvlt', ( '--help',
                                   '--force', '--link', '--trigger', ))
        for flag, opt in opts:
            if flag in ( '-v', '--verbose', ):
                _VERBOSE = True
            elif flag in ( '-l', '--link', ):
                link = True
            elif flag in ( '-t', '--trigger', ):
                trigger = True
            elif flag in ( '-o', '--open_file', ):
                return usage(1)

        if 0 == len(args):
            return usage()

        queue = args[0]

        if 1 == len(args):
            all_hosts = True

        chirp('distributing hosts for queue {0}'.format(queue))
        for item in fsq.scan(queue, lock=True, ignore_down=True, no_open=True):
            fsq.reenqueue(item, queue, hosts=args[1:],
                          all_hosts=all_hosts, link=link)
        if trigger:
            fsq.host_trigger(queue)

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
