#!/usr/bin/env python
# fsq-up(1) -- a program for turning on queues
#
# @author: O'Meara will.omeara@axialmarket.com
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os


_PROG = "fsq-down"
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
        shout('{0} [-h|--help] [-v|--verbose]'.format(
            os.path.basename(_PROG)), f)
        shout('        queue [queue [...]]', f)
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

    try:
        for arg in args:
            fsq.down(arg)
            chirp('fsq up: {0}: up'.format(arg)) 
    except fsq.FSQDownError:
        barf('{0} is down'.format(args))
    except (fsq.FSQScanError, fsq.FSQPathError, ), e:
        barf(e.strerror)
    except fsq.FSQCoerceError, e:
        barf('cannot coerce queue; charset={0}'.format(_CHARSET))
    except fsq.FSQError, e:
        shout(e.strerror.encode(_CHARSET))


if __name__ == '__main__':
    main(sys.argv)

