"""Deny IPv4/IPv6 sockets in this disposable process, then exercise the real app."""

import ctypes as C
import errno
import os
os.environ.setdefault('GSK_RENDERER','cairo')
os.environ.setdefault('GDK_DEBUG','gl-disable,vulkan-disable')
import socket
import tempfile

from workstation_monitor.native import Gio
from workstation_monitor.ui import MonitorApplication
from native_flow import pump


class Comparison(C.Structure):
    _fields_=[('arg',C.c_uint),('op',C.c_uint),('datum_a',C.c_uint64),('datum_b',C.c_uint64)]


def block_ip():
    lib=C.CDLL('libseccomp.so.2',use_errno=True)
    lib.seccomp_init.argtypes=[C.c_uint32];lib.seccomp_init.restype=C.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[C.c_char_p]
    lib.seccomp_rule_add_array.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint,C.POINTER(Comparison)]
    lib.seccomp_load.argtypes=[C.c_void_p]
    lib.seccomp_release.argtypes=[C.c_void_p]
    context=lib.seccomp_init(0x7fff0000)
    assert context
    try:
        syscall=lib.seccomp_syscall_resolve_name(b'socket')
        for family in (socket.AF_INET,socket.AF_INET6):
            rule=Comparison(0,4,int(family),0)
            assert lib.seccomp_rule_add_array(context,0x50000|errno.ENETUNREACH,syscall,1,C.byref(rule))==0
        assert lib.seccomp_load(context)==0
    finally:lib.seccomp_release(context)
    for family in (socket.AF_INET,socket.AF_INET6):
        try:socket.socket(family,socket.SOCK_STREAM)
        except OSError as exc:assert exc.errno==errno.ENETUNREACH
        else:raise AssertionError('IP socket was not blocked')


with tempfile.TemporaryDirectory() as directory:
    os.environ['WORKSTATION_MONITOR_CONFIG_DIR']=directory
    block_ip()
    app=MonitorApplication();app.set_flags(Gio.ApplicationFlags.NON_UNIQUE);app.register();app.activate()
    w=app.window;pump(2.7)
    assert w.display_frame and w.display_frame.processes
    assert w.cards['cpu'].metric.value.number is not None
    assert w.display_gpu and w.display_gpu.status=='Available'
    for category in ('GPU','Storage','Network'):
        w.open_resource(category);pump(.1)
        assert w.resource_cards
    w.close();pump(.3)
    assert all(not thread.is_alive() for thread in w.session.threads)
    app.quit()
    print('Real native app with IPv4/IPv6 sockets blocked: PASS; host networking unchanged')
