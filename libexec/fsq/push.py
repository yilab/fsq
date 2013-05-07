#!/usr/bin/env python
# fsq-push(1) -- a program for pushing queue items to remote queues
#
# @author: Jeff Rand <jeff.rand@axial.net>
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os

_PROG = "fsq-push"
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
    shout('{0} [opts] src_queue trg_queue host item_id [item_id [...]]'.format(
          os.path.basename(_PROG)), f)
    if asked_for:
        shout('{0} [-p|--protocol=jsonrpc] <proto>://<host>:<port>/url'\
                .format(os.path.basename(_PROG)), f)
        shout('{0} [-p|--protocol=jsonrpc] unix://var/sock/foo.sock'\
                .format(os.path.basename(_PROG)), f)
        shout('        src_queue trg_queue host item_id [item_id [...]]', f)
    return 0 if asked_for else fsq.const('FSQ_FAIL_PERM')

def main(argv):
    global _PROG, _VERBOSE
    protocol = 'jsonrpc'

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'vhp:', ( '--verbose',
                                                       '--help',
                                                       '--protocol=', ))
        for flag, opt in opts:
            if flag in ( '-v', '--verbose', ):
                _VERBOSE = True
            if flag in ( '-p', '--protocol', ):
                protocol = opt
            elif flag in ( '-h', '--help', ):
                return usage(1)

        if 5 > len(args):
            return usage()

        for item_id in args[4:]:
            chirp('pushing item {0} from queue {1}, host {2} to remote {3},'\
                  ' queue {4}'.format(item_id, args[1], args[3], args[0],
                                      args[2]))
            print fsq.push(args[0], args[1], item_id, args[3], args[2],
                     protocol=protocol)

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
