# coding=utf-8

from __future__ import absolute_import
import os
from pdb import Pdb
import sys
import socket
import errno

__all__ = [
    'RDB_HOST', 'RDB_PORT', 'Rdb',
    'debugger', 'set_trace',
]


RDB_HOST = os.environ.get('RDB_HOST') or '127.0.0.1'
RDB_PORT = int(os.environ.get('RDB_PORT') or 8899)

#: Holds the currently active debugger.
_current = [None]

_frame = getattr(sys, '_getframe')


class Rdb(Pdb):
    """ Remote Debugger. """

    NAME = 'Remote Debugger'
    BANNER = """{self.ident} Ready to be connected: telnet {self.host} {self.port}
{self.ident} Type 'help' for help.
{self.ident} Type 'exit' in session to continue. 
{self.ident} Waiting for client..."""
    SESSION_STARTED = '{self.ident} Now in session with {self.remote_addr}.'
    SESSION_ENDED = '{self.ident} Session with {self.remote_addr} ended.'


    def __init__(self, host=RDB_HOST, port=RDB_PORT, port_search_limit=100,
                 port_skew=+0, out=sys.stdout):
        self.active = True
        self.out = out

        self._prev_handles = sys.stdin, sys.stdout

        self._sock, self.port = self.get_avail_port(host, port, 
                            port_search_limit, port_skew)
        self.host = host
        self._sock.setblocking(True)
        self._sock.listen(1)

        self.ident = '[{0}:{1}]'.format(self.NAME, self.port)
        # prompt user
        self.output_message(self.BANNER.format(self=self))

        self._client, address = self._sock.accept()
        self._client.setblocking(True)
        self.remote_addr = ':'.join(str(v) for v in address)
        self.output_message(self.SESSION_STARTED.format(self=self))
        self._handle = sys.stdin = sys.stdout = self._client.makefile('rw')

        super(Rdb, self).__init__(completekey='tab', stdin=self._handle, stdout=self._handle)

    def get_avail_port(self, host, port, search_limit=100, skew=+0):
        current_port = None
        for i in range(search_limit):
            current_port = port + i + skew
            _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                _sock.bind((host, current_port))
            except socket.error as exc:
                if exc.errno in [errno.EADDRINUSE, errno.EINVAL]:
                    continue
                raise
            else:
                return _sock, current_port
        else:
            raise Exception("Couldn't find an available RDB port.")

    def output_message(self, message):
        print(message, file=self.out)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close_session()

    def close_session(self):
        sys.stdin, sys.stdout = self._prev_handles
        if self.active:
            _close_objs = [self._handle, self._client, self._sock]
            for _obj in _close_objs:
                if _obj is not None:
                    _obj.close()

            self.active = False
            self.output_message(self.SESSION_ENDED.format(self=self))

    def do_continue(self, arg):
        self.close_session()
        self.set_continue()
        return 1
    do_c = do_cont = do_continue

    def do_quit(self, arg):
        self.close_session()
        self.set_quit()
        return 1
    do_q = do_exit = do_quit

    def set_quit(self):
        sys.settrace(None)


def debugger():
    rdb = _current[0]
    if rdb is None or not rdb.active:
        rdb = _current[0] = Rdb()
    return rdb


def set_trace(frame=None):
    """Set break-point at current location, or a specified frame."""
    if frame is None:
        frame = _frame().f_back
    return debugger().set_trace(frame)