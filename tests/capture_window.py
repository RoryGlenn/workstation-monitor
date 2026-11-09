"""Capture only this test's X11 client window; never read desktop/browser pixels."""

import ctypes as C
from PIL import Image
import gi
gi.require_version('GdkX11','4.0')
from gi.repository import GdkX11


class XImage(C.Structure):
    _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),
              ('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),
              ('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),
              ('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),
              ('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong)]


def capture(window,path):
    x=C.CDLL('libX11.so.6')
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    display=x.XOpenDisplay(None)
    xid=window.get_surface().get_xid()
    root=C.c_ulong();xx=C.c_int();yy=C.c_int();width=C.c_uint();height=C.c_uint();border=C.c_uint();depth=C.c_uint()
    x.XGetGeometry.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),
                            C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
    assert x.XGetGeometry(display,xid,C.byref(root),C.byref(xx),C.byref(yy),C.byref(width),C.byref(height),C.byref(border),C.byref(depth))
    x.XGetImage.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
    x.XGetImage.restype=C.POINTER(XImage)
    pointer=x.XGetImage(display,xid,0,0,width.value,height.value,0xffffffff,2)
    assert pointer
    info=pointer.contents
    assert info.bits_per_pixel==32 and info.byte_order==0
    raw=C.string_at(info.data,info.bytes_per_line*info.height)
    image=Image.frombytes('RGB',(info.width,info.height),raw,'raw','BGRX',info.bytes_per_line)
    image.save(path)
    x.XDestroyImage.argtypes=[C.POINTER(XImage)];x.XDestroyImage(pointer)
    x.XCloseDisplay.argtypes=[C.c_void_p];x.XCloseDisplay(display)
    return image.size
