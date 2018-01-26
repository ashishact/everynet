# -*- coding: utf-8 -*-
from ctypes import *
from ctypes.util import find_library
import os

STDC_LIB_FILENAME = os.environ.get('STDC_LIB') or find_library('c')
if STDC_LIB_FILENAME is None:
    print "STDC LIB NOT FOUND. PLEASE DEFINE STDC_LIB"
    exit()
STDC_LIB = CDLL(STDC_LIB_FILENAME, use_errno=True)

fopen = STDC_LIB.fopen
fopen.argtypes = [c_char_p, c_char_p]
fopen.restype = c_void_p

fclose = STDC_LIB.fclose
fclose.argtypes = [c_void_p]
fclose.restype = c_int

free = STDC_LIB.free
free.argtypes = [c_void_p]
free.restype = None
