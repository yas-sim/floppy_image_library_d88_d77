from ascii_j import *

def dump_data(data:any):
    if type(data) != bytearray:
        data = bytearray(data)
    ascii_buf = ''
    for count, dt in enumerate(data):
        if count % 16 == 0:
            ascii_buf = ''
            print(f'{count:04x}', end='')
        print(f' {dt:02x}', end='')
        ascii_buf += ascii_table_half[dt]
        if count % 16 == 15:
            print(f'  {ascii_buf}')
            ascii_buf = ''
    if ascii_buf != '':
        print('   ' * (16-(count % 16)))
        print(f'  {ascii_buf}')
