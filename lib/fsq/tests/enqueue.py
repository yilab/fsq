import os
import socket
import errno
import signal
import numbers
import sys
import traceback

from . import FSQTestCase, constants as _test_c
from .internal import test_type_own_mode, normalize
# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import enqueue, venqueue, senqueue, vsenqueue, install, deconstruct,\
               constants as _c, FSQPathError, FSQInstallError,\
               FSQCoerceError, FSQConfigError

def _raise(signum, frame):
    raise IOError(errno.EAGAIN, 'Operation timed out')

def _seek(thing):
    if hasattr(thing, 'fileno'):
        try:
            os.lseek(thing.fileno(), 0, os.SEEK_SET)
        except (OSError, IOError, ), e:
            if e.errno != errno.ESPIPE:
                raise e
    elif isinstance(thing, numbers.Integral):
        try:
            os.lseek(thing, 0, os.SEEK_SET)
        except ( OSError, IOError, ), e:
            if e.errno != errno.ESPIPE:
                raise e

class TestEnqueue(FSQTestCase):
    def setUp(self):
        super(TestEnqueue, self).setUp()
        for f,payload in ((_test_c.FILE, _test_c.PAYLOAD),
                          (_test_c.NON_ASCII_FILE,
                           _test_c.NON_ASCII_PAYLOAD)):
            fd = os.open(f, os.O_WRONLY|os.O_CREAT, 00640)
            try:
                written = 0
                payload = payload.encode('utf8')
                while written < len(payload):
                    written += os.write(fd, payload[written:])
            finally:
                os.close(fd)
        os.mkfifo(_test_c.FIFO, 00640)

    def _valid_enqueue(self, queue, item, contents, args, user=None,
                       group=None, mode=None, args_should_be=None):
        args = args if args_should_be is None else args_should_be
        item_path = os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_QUEUE, item)
        # verify that we can open the file (and that it exists)
        f_item = open(item_path, 'r')
        try:
            # verify the contents
            self.assertEquals(contents, f_item.read().decode('utf8'))
            # verify that the deconstructed args equal the passed args
            self.assertEquals(list(args), deconstruct(item)[1][5:])
            # setup and test ownership and mode
            if _c.FSQ_ITEM_USER != _test_c.ORIG_ITEM_UG[0]:
                user = 1
            if _c.FSQ_ITEM_GROUP != _test_c.ORIG_ITEM_UG[1]:
                group = 1
            st = os.fstat(f_item.fileno())
            test_type_own_mode(st, item_path, 'f',
                               user if user is None else _test_c.UID,
                               group if group is None else _test_c.GID, mode)
        finally:
            f_item.close()

    def _cycle(self, fn, thing, contents, *args, **kwargs):
        _seek(thing)
        queue = args_should_be = fsq_user = fsq_group = fsq_mode = None
        if kwargs.has_key('queue'):
            queue = kwargs['queue']
            del kwargs['queue']
        if kwargs.has_key('args_should_be'):
            args_should_be = kwargs['args_should_be']
            del kwargs['args_should_be']
        if kwargs.has_key('fsq_user'):
            fsq_user = kwargs['fsq_user']
            del kwargs['fsq_user']
        if kwargs.has_key('fsq_group'):
            fsq_group = kwargs['fsq_group']
            del kwargs['fsq_group']
        if kwargs.has_key('fsq_mode'):
            fsq_mode = kwargs['fsq_mode']
            del kwargs['fsq_mode']
        if queue is None:
            queue = normalize()
            install(queue)
        if fsq_user is not None:
            _c.FSQ_ITEM_USER = fsq_user
        if fsq_group is not None:
            _c.FSQ_ITEM_GROUP = fsq_group
        if fsq_mode is not None:
            _c.FSQ_ITEM_MODE = fsq_mode
        item = fn(queue, thing, *args, **kwargs)
        if len(args) == 1 and isinstance(args[0], (list, tuple, set,)):
            args = args[0]
        self._valid_enqueue(queue, item, contents, args,
                            args_should_be=args_should_be, **kwargs)

    def _test_many_forks(self, fn, contents, *args, **kwargs):
        queue = fsq_mode = fsq_user = fsq_group = args_should_be = kind = None
        f_item = None
        if kwargs.has_key('kind'):
            kind, f_item = kwargs['kind']
            del kwargs['kind']
        if kwargs.has_key('queue'):
            queue = kwargs['queue']
            del kwargs['queue']
        if kwargs.has_key('args_should_be'):
            args_should_be = kwargs['args_should_be']
            del kwargs['args_should_be']
        if kwargs.has_key('fsq_user'):
            fsq_user = kwargs['fsq_user']
            del kwargs['fsq_user']
        if kwargs.has_key('fsq_group'):
            fsq_group = kwargs['fsq_group']
            del kwargs['fsq_group']
        if kwargs.has_key('fsq_mode'):
            fsq_mode = kwargs['fsq_mode']
            del kwargs['fsq_mode']
        if queue is None:
            queue = normalize()
            install(queue)
        if fsq_user is not None:
            _c.FSQ_ITEM_USER = fsq_user
        if fsq_group is not None:
            _c.FSQ_ITEM_GROUP = fsq_group
        if fsq_mode is not None:
            _c.FSQ_ITEM_MODE = fsq_mode
        pids = set()
        for i in range(10):
            pid = os.fork()
            # CHILD -- TRUSSED UP ENQUEUE, EXIT IF FAIL
            if pid == 0:
                try:
                    new_thing = None
                    try:
                        if kind is not None:
                            new_thing = args[0]
                            if hasattr(new_thing, 'fileno'):
                                new_thing = open(f_item.name, 'r')
                            elif isinstance(new_thing, numbers.Integral):
                                new_thing = open(f_item.name, 'r')
                                try:
                                    fd = os.dup(new_thing.fileno())
                                finally:
                                    new_thing.close()
                                new_thing = fd
                            args = (new_thing,) + args[1:]

                        for i in range(10):
                            _seek(args[0])
                            fn(queue, *args, **kwargs)
                    finally:
                        if hasattr(new_thing, 'fileno'):
                            new_thing.close()
                        elif isinstance(new_thing, numbers.Integral):
                            os.close(new_thing)

                except Exception:
                    traceback.print_exc()
                    os._exit(1)
                os._exit(0)

            pids.add(pid)

        # PARENT -- REAP
        fail = 0
        _test_c.COUNT += 100
        while len(pids):
            pid, rc = os.waitpid(-1, 0)
            pids.remove(pid)
            fail = fail or rc

        self.assertFalse(bool(fail))
        items = os.listdir(os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_QUEUE))
        self.assertEquals(len(items), 100)

        args = args[1:]
        if len(args) == 1 and isinstance(args[0], (list, tuple, set,)):
            args = args[0]
        for item in items:
            self._valid_enqueue(queue, item, contents, args,
                                args_should_be=args_should_be, **kwargs)


    def _test_socket(self, fn, payload, *args, **kwargs):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(_test_c.SOCKET)
            server.listen(5)
            for i in ('fd', 'file'):
                pid = os.fork()
                # CHILD -- FEED TESTS HERE
                if 0 == pid:
                    try:
                        client = socket.socket(socket.AF_UNIX,
                                               socket.SOCK_STREAM)
                        client.connect(_test_c.SOCKET)
                        sent = 0
                        payload = payload.encode('utf8')
                        while sent < len(payload):
                            sent += client.send(payload[sent:])
                        client.shutdown(socket.SHUT_RD)
                        client.close()
                    finally:
                        os._exit(0)
                # PARENT -- RUN TESTS HERE
                try:
                    signal.signal(signal.SIGALRM, _raise)
                    signal.alarm(10)
                    try:
                        conn, addr = server.accept()
                        try:
                            self._cycle(
                                fn, conn.fileno() if i == 'fd' else conn,
                                payload, *args, **kwargs)
                            conn.shutdown(socket.SHUT_RDWR)
                        finally:
                            conn.close()
                    finally:
                        signal.alarm(0)
                finally:
                    os.waitpid(pid, 0)
        finally:
            server.close()
            os.unlink(_test_c.SOCKET)

    def _test_fifo(self, fn, payload, *args, **kwargs):
        for i in ('fd', 'file'):
            r_fd = os.open(_test_c.FIFO, os.O_NDELAY|os.O_RDONLY)
            try:
                w_fd = os.open(_test_c.FIFO, os.O_WRONLY)
                try:
                    pid = os.fork()
                    # CHILD -- FEED TESTS HERE
                    if 0 == pid:
                        try:
                            os.close(r_fd)
                            try:
                                written = 0
                                p = payload.encode('utf8')
                                while written < len(p):
                                    written += os.write(w_fd, p[written:])
                            finally:
                                os.close(w_fd)
                        finally:
                            os._exit(0)

                    # PARENT -- RUN TESTS HERE
                    try:
                        os.close(w_fd)
                        r = None
                        if i == 'file':
                            r = os.fdopen(r_fd, 'r')
                        self._cycle(fn, r_fd if r is None else r, payload,
                                    *args, **kwargs)
                        if r is not None:
                            r.close()
                        else:
                            os.close(r_fd)
                    finally:
                        os.waitpid(pid, 0)
                finally:
                    try:
                        os.close(w_fd)
                    except (OSError, IOError,), e:
                        if e.errno != errno.EBADF:
                            raise e
            finally:
                try:
                    os.close(r_fd)
                except (OSError, IOError,), e:
                    if e.errno != errno.EBADF:
                        raise e
        pass

    def _test_pipe(self, fn, payload, *args, **kwargs):
        for i in ('fd', 'file'):
            r_fd, w_fd = os.pipe()
            try:
                pid = os.fork()
                # CHILD -- FEED TESTS HERE
                if 0 == pid:
                    try:
                        os.close(r_fd)
                        w = os.fdopen(w_fd, 'w')
                        w.write(payload.encode('utf8'))
                        w.close()
                    finally:
                        os._exit(0)

                # PARENT -- RUN TESTS HERE
                try:
                    r = None
                    os.close(w_fd)
                    if i == 'file':
                        r = os.fdopen(r_fd, 'r')
                    self._cycle(fn, r_fd if r is None else r, payload,
                                *args, **kwargs)
                    if r is not None:
                        r.close()
                    else:
                        os.close(r_fd)
                finally:
                    os.waitpid(pid, 0)
            finally:
                try:
                    os.close(r_fd)
                except (OSError, IOError,), e:
                    if e.errno != errno.EBADF:
                        raise e
                finally:
                    try:
                        os.close(w_fd)
                    except (OSError, IOError,), e:
                        if e.errno != errno.EBADF:
                            raise e

    def test_senqueue(self):
        pass

    def test_vsenqueue(self):
        pass

    def test_enqueue(self):
        '''Test enqueue, exhaustively'''
        for root in _test_c.ROOT1, _test_c.ROOT2:
            for args in ( _test_c.NORMAL, _test_c.NOT_NORMAL,
                          ( _test_c.NON_ASCII, ), _test_c.ILLEGAL_NAMES):
                for f in (_test_c.FILE, _test_c.NON_ASCII_FILE,):
                    contents = None
                    f_item = open(f, 'r')
                    try:
                        contents = f_item.read().decode('utf8')
                        os.lseek(f_item.fileno(), 0, os.SEEK_SET)
                        # test file name
                        for kind in ( f, f_item, f_item.fileno(), ):
                            self._cycle(enqueue, kind, contents, *args)
                            self._test_many_forks(enqueue, contents, kind,
                                                  *args, kind=(kind, f_item,))
                            self._test_pipe(enqueue, contents, *args)
                            self._test_fifo(enqueue, contents, *args)
                            self._test_socket(enqueue, contents, *args)
                            for uid, gid in ((_test_c.UID, _test_c.GID,),
                                             (_test_c.UNAME, _test_c.GNAME,)):
                                print >> sys.stderr, u'Tests Passed ... {0}'.format(_test_c.COUNT)
                                # user passed
                                self._cycle(enqueue, kind, contents, *args,
                                            user=uid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, user=uid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                user=uid)
                                self._test_fifo(enqueue, contents, *args,
                                                user=uid)
                                self._test_socket(enqueue, contents, *args,
                                                  user=uid)
                                # user set
                                self._cycle(enqueue, kind, contents, *args,
                                            fsq_user=uid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, fsq_user=uid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                fsq_user=uid)
                                self._test_fifo(enqueue, contents, *args,
                                                fsq_user=uid)
                                self._test_socket(enqueue, contents, *args,
                                                  fsq_user=uid)
                                # group passed
                                self._cycle(enqueue, kind, contents, *args,
                                            group=gid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, group=gid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                group=gid)
                                self._test_fifo(enqueue, contents, *args,
                                                group=gid)
                                self._test_socket(enqueue, contents, *args,
                                                  group=gid)
                                # group set
                                self._cycle(enqueue, kind, contents, *args,
                                            fsq_group=gid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, fsq_group=gid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                fsq_group=gid)
                                self._test_fifo(enqueue, contents, *args,
                                                fsq_group=gid)
                                self._test_socket(enqueue, contents, *args,
                                                  fsq_group=gid)
                                # user/group passed
                                self._cycle(enqueue, kind, contents, *args,
                                            user=uid, group=gid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, user=uid,
                                                      group=gid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                user=uid, group=gid)
                                self._test_fifo(enqueue, contents, *args,
                                                user=uid, group=gid)
                                self._test_socket(enqueue, contents, *args,
                                                  user=uid, group=gid)
                                # user/group set
                                self._cycle(enqueue, kind, contents, *args,
                                            fsq_user=uid, fsq_group=gid)
                                self._test_many_forks(enqueue, contents, kind,
                                                      *args, fsq_user=uid,
                                                      fsq_group=gid,
                                                      kind=(kind, f_item,))
                                self._test_pipe(enqueue, contents, *args,
                                                fsq_user=uid, fsq_group=gid)
                                self._test_fifo(enqueue, contents, *args,
                                                fsq_user=uid, fsq_group=gid)
                                self._test_socket(enqueue, contents, *args,
                                                  fsq_user=uid, fsq_group=gid)

                    finally:
                        f_item.close()

    def test_venqueue(self):
        pass
