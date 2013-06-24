#!/usr/bin/env python
# fsq -- a python library for manipulating and introspecting FSQ queues
# @author: Jeff Rand <jeff.rand@axial.net>
# @author: Jacob Yuan<jacob.yuan@axial.net>
#
# fsq/jsonprcd.py -- a server for pushing queue items to remotes
#     fsq is all unicode internally, if you pass in strings,
#     they will be explicitly coerced to unicode.
#
#   NB: changes to environment following first import, will not
#       affect values potentially a bug to clean up later.
#
# This software is for POSIX compliant systems only.

import errno
import os
import signal
import sys
import getopt
import jsonrpclib

from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCRequestHandler as handler,\
                                           SimpleJSONRPCServer as server


_PROG = os.path.basename(sys.argv[0])
_OPTIONS = "w:vht"
_LONG_OPTS = ("workers=", "json-rpc-version=",  "verbose", "help", 'trigger', )
_USAGE = ("usage: {0} [-w|--workers=<n>] "
          "[-v|--verbose] [-h|--help] [-t|--trigger] <host> <port>".format(_PROG))
_JSONRPC_V = 1.0
_N_FORKS = 5
_REQ_QSIZE = 5
_POLL_INTERVAL = 1.0
_ERR_EXIT = 100

_MASKED_SIGS = (signal.SIGABRT, signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
_SIG_HANDLERS = dict([(sig, signal.getsignal(sig)) for sig in _MASKED_SIGS])
_PROPAGATED_SIGS = _MASKED_SIGS
_cpids = []
_signalled = 0
_deferred_sig = 0

def _api_version(): return "1.0"

def shout(msg, fobj=sys.stderr):
    print >> fobj, "{0}: {1}".format(_PROG, msg)
    return

def barf(msg, exit_code=_ERR_EXIT, fobj=sys.stderr):
    shout(msg, fobj=fobj)
    sys.exit(exit_code)

def _propagate_sig(signum, frame):
    global _signalled
    _signalled = signum
    for pid in _cpids:
        os.kill(pid, signum)
    return

def _defer_sig(signum, frame):
    global _deferred_sig
    _deferred_sig = signum
    return

def _noisy(func, verbose, pull_trigger):
    def decorated(*args, **kwargs):
        from fsq import trigger_pull, FSQTriggerPullError, is_down
        if verbose:
            shout('calling {0}: with args:{1}, kwargs: {2}'.format(
                func.__name__, args, kwargs))
        ret = func(*args, **kwargs)
        if verbose:
            shout('{0} returned: {1}'.format(func.__name__, ret))
        trg_queue = args[1]
        if pull_trigger and not is_down(trg_queue):
            try:
                trigger_pull(trg_queue)
            except FSQTriggerPullError:
                pass
    decorated.__name__ = func.__name__
    return decorated

def _spawn_worker(proxy, verbose, pull_trigger, func, *args, **kwargs):
    pid = os.fork()
    if pid == 0:
        for sig in _MASKED_SIGS:
            signal.signal(sig, _SIG_HANDLERS[sig])

        from fsq.remote import v1

        for f in (v1.__dict__[s] for s in v1.__all__):
            if not callable(f):
                barf("error: not a callable function: {0}".format(f))
            proxy.register_function(_noisy(f, verbose, pull_trigger))
        proxy.register_introspection_functions()
        proxy.register_function(_api_version, 'api_version')

        try:
            func(*args, **kwargs)
        except OSError, e:
            if e.errno == errno.EINTR: os._exit(1)
            elif e.errno == errno.ESRCH: os._exit(2)
            os._exit(3)
        except (KeyboardInterrupt, Exception):
            os._exit(4)
        os._exit(0)
    else:
        return pid

class MaskedHandler(handler):
    def setup(self):
        for sig in _MASKED_SIGS:
            signal.signal(sig, _defer_sig)
        return handler.setup(self)

    def handle(self):
        return handler.handle(self)

    def finish(self):
        for sig in _MASKED_SIGS:
            signal.signal(sig, _SIG_HANDLERS[sig])
        if _deferred_sig:
            os.kill(os.getpid(), _deferred_sig)
        return handler.finish(self)

def main(argv):
    global _cpids, _deferred_sig, _signalled
    host = port = None
    verbose = False
    pull_trigger = False
    jsonrpc_v = _JSONRPC_V
    n_forks = _N_FORKS

    try:
        opts, args = getopt.getopt(argv[1:], _OPTIONS, _LONG_OPTS)
    except getopt.GetoptError, e:
        barf("error: {0}".format(e))
    for opt, arg in opts:
        if opt in ("-w", "--workers="):
            n_forks = int(arg)
        elif opt in ("-t", "--trigger"):
            pull_trigger = True
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-h", "--help"):
            print _USAGE ; return 0
        else:
            barf("error: unhandled option: `{0}'".format(opt))


    if len(args) < 2:
        barf("error: insufficient arguments for host, port: parsed {0}".\
             format(", ".join(args if args else [str(None)])))
    host, port = str(args[0]), int(args[1])

    if n_forks < 1:
        barf("error: the number of workers is less than 1: parsed {0}".format(n_forks))

    jsonrpclib.config.version = 1.0
    jsonrpc_srv = server((host, port), logRequests=verbose,
                          requestHandler=MaskedHandler, encoding='utf-8')

    for i in xrange(n_forks):
        pid = _spawn_worker(jsonrpc_srv, verbose, pull_trigger,
                            jsonrpc_srv.serve_forever,
                            poll_interval=_POLL_INTERVAL)
        _cpids.append(pid)

    shout("starting {0} json-rpc {1} server on: {2}:{3}".format(
            _PROG, jsonrpc_v, host, port))
    if verbose:
        shout("parent pid: {0}, child pids: {1}".format(
                os.getpid(), ", ".join((str(p) for p in _cpids))))

    for sig in _PROPAGATED_SIGS:
        signal.signal(sig, _propagate_sig)

    _rpids = []
    _exit_status = 0
    while _cpids:
        try:
            pid, rc = os.waitpid(-1, 0)
            if not os.WIFEXITED(rc):
                _exit_status = _ERR_EXIT
                if os.WIFSIGNALED(rc):
                    shout("pid {0} received signal {1}".format(pid, os.WTERMSIG(rc)))
                else:
                    shout("pid {0} abnormal termination".format(pid))
            else:
                _exit_status = os.WEXITSTATUS(rc)
                shout("pid {0} exit status: {1}".format(pid, _exit_status))

            _cpids.remove(pid)
            if not _signalled or _signalled == signal.SIGHUP:
                p = _spawn_worker(jsonrpc_srv, verbose,
                                  jsonrpc_srv.serve_forever,
                                  poll_interval=_POLL_INTERVAL)
                _rpids.append(p)

            if len(_cpids) == 0 and len(_rpids) > 0:
                _cpids = _rpids
                _rpids = []
                c_status = "reloaded" if _signalled == signal.SIGHUP else "respawned"
                _deferred_sig = _signalled = 0
                shout("{0} pids: {1}".format(c_status, ", ".join((str(p) for p in _cpids))))
        except OSError, e:
            if e.errno == errno.EINTR:
                continue
            elif e.errno == errno.ESRCH:
                if pid: _cpids.remove(pid)
                else: shout("nonexistent process")
            raise e

    shout("exit status: {0}".format(_exit_status))
    return _exit_status

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt, e:
        barf("received signal {0}".format(signal.SIGINT))
    except Exception, e:
        barf("unexpected error: {0}".format(e))


