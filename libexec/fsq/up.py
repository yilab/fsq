#!/usr/bin/env python
# fsq-up(1) -- a program for turning on queues
#
# @author: O'Meara will.omeara@axial.net
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os


_PROG = "fsq-up"
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
    shout('{0} [opts] queue [queue [...]]'.format(
          os.path.basename(_PROG)), f)
    if asked_for:
        shout('{0} [-h|--help] [-v|--verbose]'.format(
            os.path.basename(_PROG)), f)
        shout('        queue [queue [...]]', f)
    sys.exit(exit)


# all fsq commands use a main function
def main(argv):
    global _PROG, _VERBOSE

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'hvd:', ( 'help', 'down-file'))
    except getopt.GetoptError, e:
        barf('invalid flag: -{0}{1}'.format('-' if 1 < len(e.opt) else '',
             e.opt))
    try:
        for flag, opt in opts:
            if '-v' == flag or '--verbose' == flag:
                _VERBOSE = True
            elif '-h' == flag or '--help' == flag:
                usage(1)
    except ( fsq.FSQEnvError, fsq.FSQCoerceError, ):
        barf('invalid argument for flag: {0}'.format(flag))

    for arg in args:
        try:
                fsq.up(arg)
                chirp('{0}: up'.format(arg))
        except fsq.FSQCoerceError, e:
            barf('cannot coerce queue; charset={0}'.format(_CHARSET))
        except fsq.FSQError, e:
            barf(e.strerror.encode(_CHARSET))


if __name__ == '__main__':
    main(sys.argv)
