#!/usr/bin/env python
# fsq-install(1) -- a program for installing a fsq queue.
#
# @author: Matthew Story <matt.story@axial.net>
# @author: Jeff Rand <jeff.rand@axial.net>
# @depends: fsq(1), fsq(7), python (>=2.7)
#
# This software is for POSIX compliant systems only.
import getopt
import sys
import fsq
import os
import errno

_PROG = "fsq-install"
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
        shout('{0} [-h|--help] [-v|--verbose] [-f|--force]'\
              ' [-d|--down]'.format(os.path.basename(_PROG)), f)
        shout('        [-t|--triggered] [-i|--ignore-exists]', f)
        shout('        [-o owner|--owner=user|uid]', f)
        shout('        [-g group|--group=group|gid]', f)
        shout('        [-m mode|--mode=int]', f)
        shout('        [-a host|--add-host=host]', f)
        shout('        queue [queue [...]]', f)
    return 0 if asked_for else fsq.const('FSQ_FAIL_PERM')

def main(argv):
    global _PROG, _VERBOSE
    force = False
    is_down = False
    is_triggered = False
    is_host_triggered = False
    ignore = False
    flag = None
    hosts = []

    _PROG = argv[0]
    try:
        opts, args = getopt.getopt(argv[1:], 'hvfdto:g:m:ia:', ( '--help',
                                   '--verbose', '--force', '--down',
                                   '--triggered', '--owner', '--group',
                                   '--mode', '--ignore-exists', '--add-host',))
        for flag, opt in opts:
            if flag in ( '-v', '--verbose', ):
                _VERBOSE = True
            elif flag in ( '-f', '--force', ):
                force = True
            elif flag in ( '-d', '--down', ):
                is_down = True
            elif flag in ( '-t', '--triggered', ):
                is_triggered = True
            elif flag in ( '-i', '--ignore-exists', ):
                ignore = True
            elif flag in ( '-o', '--owner', ):
                for c in ( 'FSQ_QUEUE_USER', 'FSQ_ITEM_USER', ):
                    fsq.set_const(c, opt)
            elif flag in ( '-g', '--group', ):
                for c in ( 'FSQ_QUEUE_GROUP', 'FSQ_ITEM_GROUP', ):
                    fsq.set_const(c, opt)
            elif flag in ( '-m', '--mode', ):
                for c in ( 'FSQ_QUEUE_MODE', 'FSQ_ITEM_MODE', ):
                    fsq.set_const(c, opt)
            elif flag in ( '-a', '--add-host', ):
                hosts.append(opt)
            elif flag in ( '-h', '--help', ):
                return usage(1)

        if 0 == len(args):
            return usage()
        if hosts and is_triggered:
            is_host_triggered = True
        for queue in args:
            try:
                chirp('installing {0} to {1}'.format(queue,
                                                     fsq.const('FSQ_ROOT')))
                fsq.install(queue, is_down=is_down, is_triggered=is_triggered,
                            hosts=hosts or None,
                            is_host_trigered=is_host_triggered)
            except fsq.FSQInstallError, e:
                if e.errno == errno.ENOTEMPTY or e.errno == errno.ENOTDIR:
                    if force:
                        fsq.uninstall(queue)
                        fsq.install(queue)
                    elif ignore:
                        chirp('skipping {0}; already installed'.format(queue))
                    else:
                        raise
                else:
                    raise

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
