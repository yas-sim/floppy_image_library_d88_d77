import typing

from fdimagelib.ascii_j import *
from fdimagelib.floppy_image import *

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

def open_image(file_name:str, image_number:str, verbose:bool=False) -> typing.Tuple[FLOPPY_IMAGE_D88, FLOPPY_DISK_D88]:
    if file_name == '':
        return
    if os.path.exists(file_name) == False:
        raise FileNotFoundError
    image_file = FLOPPY_IMAGE_D88()
    image_file.read_file(file_name)

    num_images = image_file.get_num_images()
    if verbose:
        print(f'{num_images} images detected.')
    image_number = int(image_number)
    if image_number >= num_images:
        raise ValueError
    disk_image = image_file.images[image_number]
    return image_file, disk_image

def attributes_to_string(file_type:int, ascii_flag:int, random_access_flag:int) -> typing.Tuple[str, str, str]:
    file_type_str = str(file_type) if file_type >=0 and file_type <= 2 else '?'
    ascii_flag_str = 'B' if ascii_flag == 0x00 else 'A' if ascii_flag == 0xff else '?'
    random_access_flag_str = 'S' if random_access_flag == 0x00 else 'R' if random_access_flag == 0xff else '?'
    return (file_type_str, ascii_flag_str, random_access_flag_str)

def string_to_attributes(attribute_string:str):
    """
    Expecging concatenated string of file_type, ascii_flag and random_access_flag such as "2B0".
    """
    match attribute_string[0]:
        case '0' | '1' | '2':
            file_type = int(attribute_string[0])
        case _:
            file_type = -1
    match attribute_string[1]:
        case 'B' | 'b':
            ascii_flag = 0x00
        case 'A' | 'a':
            ascii_flag = 0xff
        case _:
            ascii_flag = -1
    match attribute_string[2]:
        case 'S' | 's':
            random_access_flag = 0x00
        case 'R' | 'r':
            random_access_flag = 0xff
        case _:
            random_access_flag = -1
    return (file_type, ascii_flag, random_access_flag)    
