import os
import socket
import errno
import signal
import sys

from . import FSQTestCase, constants as _test_c
from .internal import test_type_own_mode, normalize
# FROM PAPA-BEAR IMPORT THE FOLLOWING
from .. import enqueue, venqueue, senqueue, vsenqueue, install, deconstruct,\
               constants as _c, FSQPathError, FSQInstallError,\
               FSQCoerceError, FSQConfigError

def _raise(signum, frame):
    raise IOError(errno.EAGAIN, 'Operation timed out')

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
        f_item = open(item_path, 'r+')
        try:
            # verify the contents
            f_item.seek(0)
            self.assertEquals(contents, f_item.read().decode('utf8'))
            # verify that the deconstructed args equal the passed args
            self.assertEquals(args, deconstruct(item)[1][5:])
            # setup and test ownership and mode
            if _c.FSQ_ITEM_USER != _test_c.ORIG_ITEM_UG[0]:
                user = 1
            if _c.FSQ_ITEM_GROUP != _test_c.ORIG_ITEM_UG[1]:
                group = 1
            st = os.fstat(f_item.fileno())
            test_type_own_mode(st, item_path, 'f',
                               user if user is None else UID,
                               group if group is None else GID, mode)
        finally:
            f_item.close()

    def _cycle(self, fn, thing, contents, *args, **kwargs):
        queue = args_should_be = None
        if kwargs.has_key('queue'):
            queue = kwargs['queue']
            del kwargs['queue']
        if kwargs.has_key('args_should_be'):
            args_should_be = kwargs['args_should_be']
            del kwargs['args_should_be']
        if queue is None:
            queue = normalize()
            install(queue)
        item = fn(queue, thing, *args, **kwargs)
        if len(args) == 1 and isinstance(args[0], (list, tuple, set,)):
            args = args[0]
        self._valid_enqueue(queue, item, contents, args,
                            args_should_be=args_should_be, **kwargs)

    def _test_many_forks(self, fn, contents, *args, **kwargs):
        queue = normalize()
        install(queue)
        if kwargs.has_key('queue'):
            queue = kwargs['queue']
            del kwargs['queue']
        args_should_be = None
        if kwargs.has_key('args_should_be'):
            args_should_be = kwargs['args_should_be']
            del kwargs['args_should_be']
        pids = set()
        for i in range(10):
            pid = os.fork()
            # CHILD -- TRUSSED UP ENQUEUE, EXIT IF FAIL
            if pid == 0:
                try:
                    fn(queue, *args, **kwargs)
                except Exception, e:
                    print >> sys.stderr, e
                    os._exit(1)
                os._exit(0)
            pids.add(pid)

        # PARENT -- REAP
        fail = 0
        while len(pids):
            pid, rc = os.waitpid(-1, 0)
            pids.remove(pid)
            fail = fail or rc

        self.assertFalse(bool(fail))
        items = os.listdir(os.path.join(_c.FSQ_ROOT, queue, _c.FSQ_QUEUE))
        self.assertEquals(len(items), 10)
 
        if len(args) == 2 and isinstance(args[1], (list, tuple, set,)):
            args = args[1]
        for item in items:
            self._valid_enqueue(queue, item, contents, args,
                                args_should_be=args_should_be, **kwargs)


    def _test_socket(self, fn, *args, **kwargs):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(_test_c.SOCKET)
            server.listen(5)
            for payload in ( _test_c.PAYLOAD, _test_c.NON_ASCII_PAYLOAD, ):
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
                                s = None
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

    def _test_fifo(self, fn, *args, **kwargs):
        #for payload in ( _test_c.PAYLOAD, _test_c.NON_ASCII_PAYLOAD, ):
        #    for i in ('fd', 'file'):
        pass

    def _test_pipe(self, fn, *args, **kwargs):
        for payload in ( _test_c.PAYLOAD, _test_c.NON_ASCII_PAYLOAD, ):
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
        self._test_pipe(venqueue, [])
        self._test_socket(venqueue, [])
        for f in (_test_c.FILE, _test_c.NON_ASCII_FILE,):
            f_item = open(f, 'r')
            try:
                self._test_many_forks(venqueue, f_item.read().decode('utf8'), f, [])
            finally:
                f_item.close()

    def test_venqueue(self):
        pass
