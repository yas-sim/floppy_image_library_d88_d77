from fbasic_utils import *

a = bytearray([0x90, 0x7c, 0x00, 0x00])
b = decode_float(a)
print(hex(int(b)))
