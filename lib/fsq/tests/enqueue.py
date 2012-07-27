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
               constants as _c, FSQPathError, FSQCoerceError,\
               FSQEnqueueError, FSQEncodeError

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
        fsq_queue = fsq_charset = None
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
        if kwargs.has_key('fsq_queue'):
            fsq_queue = kwargs['fsq_queue']
            _c.FSQ_QUEUE = fsq_queue
            del kwargs['fsq_queue']
        if kwargs.has_key('fsq_charset'):
            fsq_charset = kwargs['fsq_charset']
            del kwargs['fsq_charset']
        if queue is None:
            queue = normalize()
            install(queue)
        if fsq_user is not None:
            _c.FSQ_ITEM_USER = fsq_user
        if fsq_group is not None:
            _c.FSQ_ITEM_GROUP = fsq_group
        if fsq_mode is not None:
            _c.FSQ_ITEM_MODE = fsq_mode
        if fsq_charset is not None:
            _c.FSQ_CHARSET = fsq_charset
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

    def _run_gammit(self, fn, file_or_str, var_args):
        items = [_test_c.FILE, _test_c.NON_ASCII_FILE,]
        contents = tuple()
        file_items = []
        kind = None

        # setup file or string
        for item in items:
            f_item = open(item, 'r')
            try:
                contents += (f_item.read().decode('utf8'),)
            finally:
                f_item.close()

        if file_or_str == 's':
            items = list(contents)
        else:
            kind = True

        arg_sets = [ _test_c.NORMAL, _test_c.NOT_NORMAL,
                       ( _test_c.NON_ASCII, ), _test_c.ILLEGAL_NAMES ]
        if not var_args:
            for ind in range(len(arg_sets)):
                arg_sets[ind] = (arg_sets[ind],)

        try:
            for ind in range(len(items)):
                if file_or_str == 's':
                    items[ind] = (items[ind],)
                else:
                    file_items.append(open(items[ind], 'r'))
                    items[ind] = ( items[ind], file_items[ind],
                                   file_items[ind].fileno(), )
                items[ind] = (items[ind], contents[ind],)

            del contents
            for root in _test_c.ROOT1, _test_c.ROOT2:
                for args in arg_sets:
                    for ind in range(len(items)):
                        f_item = None
                        if file_or_str != 's':
                            f_item = file_items[ind]
                        item_kinds,contents = items[ind]
                        for item in item_kinds:
                            self._cycle(fn, item, contents, *args)
                            self._cycle(fn, item, contents, *args,
                                        fsq_queue=_test_c.NOT_NORMAL[0])
                            self._test_many_forks(fn, contents, item,
                                                  *args, kind=(kind, f_item,))
                            if file_or_str != 's':
                                self._test_pipe(fn, contents, *args)
                                self._test_fifo(fn, contents, *args)
                                self._test_socket(fn, contents, *args)

                            for uid, gid in ((_test_c.UID, _test_c.GID,),
                                             (_test_c.UNAME, _test_c.GNAME,)):
                                print >> sys.stderr, u'{0} passed {1} tests'\
                                                     u' ...'.format(
                                    fn.__name__, _test_c.COUNT)
                                # user passed
                                self._cycle(fn, item, contents, *args,
                                            user=uid)
                                self._cycle(fn, item, contents, *args,
                                            user=uid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, user=uid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    user=uid)
                                    self._test_fifo(fn, contents, *args,
                                                    user=uid)
                                    self._test_socket(fn, contents, *args,
                                                      user=uid)
                                # user set
                                self._cycle(fn, item, contents, *args,
                                            fsq_user=uid)
                                self._cycle(fn, item, contents, *args,
                                            fsq_user=uid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, fsq_user=uid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    fsq_user=uid)
                                    self._test_fifo(fn, contents, *args,
                                                    fsq_user=uid)
                                    self._test_socket(fn, contents, *args,
                                                      fsq_user=uid)
                                # group passed
                                self._cycle(fn, item, contents, *args,
                                            group=gid)
                                self._cycle(fn, item, contents, *args,
                                            group=gid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, group=gid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    group=gid)
                                    self._test_fifo(fn, contents, *args,
                                                    group=gid)
                                    self._test_socket(fn, contents, *args,
                                                      group=gid)
                                # group set
                                self._cycle(fn, item, contents, *args,
                                            fsq_group=gid)
                                self._cycle(fn, item, contents, *args,
                                            fsq_group=gid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, fsq_group=gid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    fsq_group=gid)
                                    self._test_fifo(fn, contents, *args,
                                                    fsq_group=gid)
                                    self._test_socket(fn, contents, *args,
                                                      fsq_group=gid)
                                # user/group passed
                                self._cycle(fn, item, contents, *args,
                                            user=uid, group=gid)
                                self._cycle(fn, item, contents, *args,
                                            user=uid, group=gid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, user=uid,
                                                      group=gid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    user=uid, group=gid)
                                    self._test_fifo(fn, contents, *args,
                                                    user=uid, group=gid)
                                    self._test_socket(fn, contents, *args,
                                                      user=uid, group=gid)
                                # user/group set
                                self._cycle(fn, item, contents, *args,
                                            fsq_user=uid, fsq_group=gid)
                                self._cycle(fn, item, contents, *args,
                                            fsq_user=uid, fsq_group=gid,
                                            fsq_queue=_test_c.NOT_NORMAL[0])
                                self._test_many_forks(fn, contents, item,
                                                      *args, fsq_user=uid,
                                                      fsq_group=gid,
                                                      kind=(kind, f_item,))
                                if file_or_str != 's':
                                    self._test_pipe(fn, contents, *args,
                                                    fsq_user=uid,
                                                    fsq_group=gid)
                                    self._test_fifo(fn, contents, *args,
                                                    fsq_user=uid,
                                                    fsq_group=gid)
                                    self._test_socket(fn, contents, *args,
                                                      fsq_user=uid,
                                                      fsq_group=gid)
        finally:
            for item in file_items:
                item.close()

    def test_badpath(self):
        item = open(_test_c.FILE, 'r')
        try:
            for name in _test_c.ILLEGAL_NAMES:
                queue = normalize()
                install(queue)
                _c.FSQ_QUEUE = name
                self.assertRaises(FSQPathError, enqueue, queue, item)

                queue = normalize()
                install(queue)
                _c.FSQ_QUEUE = name
                self.assertRaises(FSQPathError, venqueue, queue, item, [])

                queue = normalize()
                install(queue)
                _c.FSQ_QUEUE = name
                self.assertRaises(FSQPathError, senqueue, queue, item.read())
                _seek(item)

                queue = normalize()
                install(queue)
                _c.FSQ_QUEUE = name
                self.assertRaises(FSQPathError, senqueue, queue, item.read())
                _seek(item)
        finally:
            item.close()

    def test_coercearg(self):
        item = open(_test_c.FILE, 'r')
        try:
            contents = item.read().decode('utf8')
            _seek(item)
            nargs = ( _test_c.NON_ASCII.encode('utf8'), )
            vargs = (nargs,)
            args_should_be = ( _test_c.NON_ASCII, )
            for fn, itm, args in ( ( enqueue, item, nargs, ),
                                   ( venqueue, item, vargs, ),
                                   ( senqueue, contents.encode('utf8'), nargs, ),
                                   ( vsenqueue, contents.encode('utf8'), vargs, ) ):
                self._cycle(fn, itm, contents, *args,
                            args_should_be=args_should_be)
                self.assertRaises(FSQCoerceError, self._cycle, fn, itm,
                                  contents, *args,
                                  args_should_be=args_should_be,
                                  fsq_charset='ascii')
        finally:
            item.close()

    def test_badenqueue(self):
        for f in (_test_c.ILLEGAL_FD, _test_c.ILLEGAL_FILE,):
            queue = normalize()
            install(queue)
            self.assertRaises(FSQEnqueueError, enqueue, queue, f)

            queue = normalize()
            install(queue)
            self.assertRaises(FSQEnqueueError, venqueue, queue, f, [])

    def test_badsenqueue(self):
        for s in (_test_c.ILLEGAL_STR,):
            queue = normalize()
            install(queue)
            self.assertRaises(TypeError, senqueue, queue, s)

            queue = normalize()
            install(queue)
            self.assertRaises(TypeError, vsenqueue, queue, s, [])

    def test_badconstruct(self):
        item = open(_test_c.FILE, 'r')
        try:
            for name in _test_c.ILLEGAL_NAMES:
                # assert failure for bad encode char
                queue = normalize()
                install(queue)
                _c.FSQ_ENCODE = _test_c.ILLEGAL_ENCODE
                self.assertRaises(FSQEncodeError, enqueue, queue, item)
                self.assertRaises(FSQEncodeError, venqueue, queue, item, [])
                self.assertRaises(FSQEncodeError, senqueue, queue,
                                  item.read())
                _seek(item)
                self.assertRaises(FSQEncodeError, vsenqueue, queue,
                                  item.read(), [])
                _seek(item)
                queue = normalize()
                install(queue)
                _c.FSQ_DELIMITER = _test_c.ILLEGAL_ENCODE
                self.assertRaises(FSQEncodeError, enqueue, queue, item)
                self.assertRaises(FSQEncodeError, venqueue, queue, item, [])
                self.assertRaises(FSQEncodeError, senqueue, queue,
                                  item.read())
                _seek(item)
                self.assertRaises(FSQEncodeError, vsenqueue, queue,
                                  item.read(), [])
                _seek(item)

                # assert failure for non coercable arg
                queue = normalize()
                install(queue)
                self.assertRaises(FSQCoerceError, enqueue, queue, item,
                                  [_test_c.ILLEGAL_NAME])
                self.assertRaises(FSQCoerceError, venqueue, queue, item,
                                  [[_test_c.ILLEGAL_NAME],])
                self.assertRaises(FSQCoerceError, senqueue, queue,
                                  item.read(), [_test_c.ILLEGAL_NAME])
                _seek(item)
                self.assertRaises(FSQCoerceError, vsenqueue, queue,
                                  item.read(), [[_test_c.ILLEGAL_NAME],])
                _seek(item)

                # non-ascii encodeseq
                queue = normalize()
                install(queue)
                _c.FSQ_ENCODE = _test_c.NON_ASCII
                self.assertRaises(FSQEncodeError, enqueue, queue, item)
                self.assertRaises(FSQEncodeError, venqueue, queue, item, [])
                self.assertRaises(FSQEncodeError, senqueue, queue,
                                  item.read())
                _seek(item)
                self.assertRaises(FSQEncodeError, vsenqueue, queue,
                                  item.read(), [])
                _seek(item)

                # non-ascii delimiter
                queue = normalize()
                install(queue)
                _c.FSQ_DELIMITER = _test_c.NON_ASCII
                self.assertRaises(FSQEncodeError, enqueue, queue, item)
                self.assertRaises(FSQEncodeError, venqueue, queue, item, [])
                self.assertRaises(FSQEncodeError, senqueue, queue,
                                  item.read())
                _seek(item)
                self.assertRaises(FSQEncodeError, vsenqueue, queue,
                                  item.read(), [])
                _seek(item)

                # delimiter and encodeseq set to be same
                queue = normalize()
                install(queue)
                normalize()
                _c.FSQ_DELIMITER = _c.FSQ_ENCODE
                self.assertRaises(FSQEncodeError, enqueue, queue, item)
                self.assertRaises(FSQEncodeError, venqueue, queue, item, [])
                self.assertRaises(FSQEncodeError, senqueue, queue,
                                  item.read())
                _seek(item)
                self.assertRaises(FSQEncodeError, vsenqueue, queue,
                                  item.read(), [])
                _seek(item)
        finally:
            item.close()

    def test_permdenied(self):
        '''Test proper failure for permission denied'''
        # test permission denied root
        queue = normalize()
        install(queue)
        os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0)
        try:
            item = open(_test_c.FILE, 'r')
            try:
                self.assertRaises(FSQEnqueueError, enqueue, queue, item)
                self.assertRaises(FSQEnqueueError, venqueue, queue, item, [])
                self.assertRaises(FSQEnqueueError, senqueue, queue, item.read())
                _seek(item)
                self.assertRaises(FSQEnqueueError, vsenqueue, queue, item.read(), [])
            finally:
                item.close()
        finally:
            os.chmod(os.path.join(_c.FSQ_ROOT, queue), 0750)

    def test_enqueue(self):
        '''Test enqueue, exhaustively'''
        self._run_gammit(enqueue, 'f', True)

    def test_venqueue(self):
        '''Test venqueue, exhaustively'''
        self._run_gammit(venqueue, 'f', False)

    def test_senqueue(self):
        '''Test senqueue, exhaustively'''
        queue = normalize()
        install(queue)
        self.assertRaises(FSQCoerceError, senqueue, queue, _test_c.NON_ASCII,
                          charset='ascii')
        self._run_gammit(senqueue, 's', True)

    def test_vsenqueue(self):
        '''Test vsenqueue, exhaustively'''
        queue = normalize()
        install(queue)
        self.assertRaises(FSQCoerceError, senqueue, queue, _test_c.NON_ASCII,
                          [], charset='ascii')
        self._run_gammit(vsenqueue, 's', False)
