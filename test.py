import os, sys
import unittest

import time
import timeit

import subprocess

import fdimagelib

def create_new_image():
    new_image = fdimagelib.FLOPPY_IMAGE_D88()
    new_image.create_and_add_new_empty_image()
    new_disk = new_image.images[0]
    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(new_disk)
    fs.logical_format()
    return new_image


class TestDiskImage(unittest.TestCase):
    test_image_file = 'fb_toolbox.d77'


    def test_file_load(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file(TestDiskImage.test_image_file)

        disk_image = image_file.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        fs.dump_valid_directory()
        fs.dump_FAT()

    def test_get_directory_entries(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file(TestDiskImage.test_image_file)

        disk_image = image_file.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        entries = fs.get_valid_directory_entries()
        for entry in entries:
            print(entry)


    def test_image_access(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file(TestDiskImage.test_image_file)


    def test_basic_ir_decoding(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file('fb_toolbox.d77')

        disk_image = image_file.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        fs.dump_valid_directory()
        fs.dump_FAT()

        data = fs.read_file('ASM09')
        basic_ir = fs.extract_file_contents(data['data'], data['file_type'], data['ascii_flag'])
        basic_text = fdimagelib.F_BASIC_IR_decode(basic_ir['data'])
        print()
        print(basic_text)


    def test_read_file_by_idx(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file('fb_toolbox.d77')

        disk_image = image_file.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        fs.dump_valid_directory()
        fs.dump_FAT()

        data = fs.read_file_by_idx(3)
        basic_ir = fs.extract_file_contents(data['data'], data['file_type'], data['ascii_flag'])
        basic_text = fdimagelib.F_BASIC_IR_decode(basic_ir['data'])
        print()
        print(basic_text)


    def test_create_new_image(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(new_disk)
        fs.logical_format()
        print(fs.check_disk_id())
        print(fs.image.read_sector_LBA(2))
        fs.dump_valid_directory()
        fs.dump_FAT()


    def test_create_new_file(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(new_disk)
        fs.logical_format()
        print(fs.check_disk_id())
        print(fs.image.read_sector_LBA(2))
        dummy = bytearray([0x02 for _ in range(256 * 20)])
        fs.dump_valid_directory()
        fs.write_file('TESTFILE', dummy, 0, 0, 0)
        fs.dump_valid_directory()
        fs.dump_FAT()


    def test_delete_file(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(new_disk)
        fs.logical_format()
        print(fs.check_disk_id())
        print(fs.image.read_sector_LBA(2))
        dummy = bytearray([0x02 for _ in range(256 * 20)])
        fs.dump_valid_directory()
        fs.write_file('FILE1', dummy, 0, 0, 0)
        fs.write_file('FILE2', dummy, 0, 0, 0)
        fs.write_file('FILE3', dummy, 0, 0, 0)
        fs.dump_valid_directory()
        fs.delete_file('FILE2')
        fs.dump_valid_directory()
        fs.dump_FAT()
        dirs = fs.get_valid_directory_entries()
        assert len(dirs) == 2


    def test_basic_image_access(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        data = bytearray(range(256))
        new_disk.write_sector_LBA(2, data)
        data = data[::-1]
        new_disk.write_sector(0, (0,0,1), data)

        data = new_disk.read_sector_LBA(2)
        print(data)
        data = new_disk.read_sector(0, (0, 0, 1))
        print(data)


    def test_write_image(self):
        image_file = fdimagelib.FLOPPY_IMAGE_D88()
        image_file.read_file('fb_toolbox.d77')

        disk_image = image_file.images[0]

        fs = fdimagelib.FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        data = fs.read_file('ASM09EB')
        print("data", len(data['data']))
        fs.dump_FAT()
        fs.write_file('ASM09CP', data['data'], data['file_type'], data['ascii_flag'], data['random_access_flag'])
        fs.dump_valid_directory()
        image_file.write_file('test.d77')
        fs.dump_FAT()


    def test_serialize_deserialize(self):
        file_names = [ 'test.yaml', 'test.json' ]
        hex_dumps = [ True, False ]
        for file_name in file_names:
            for hex_dump in hex_dumps:
                print(f'file name:{file_name}, hex dump:{hex_dump}')
                if True:
                    new_image = fdimagelib.FLOPPY_IMAGE_D88()
                    new_image.read_file(TestDiskImage.test_image_file)
                    new_disk = new_image.images[0]
                    t = timeit.timeit(lambda: new_disk.serialize(file_name, hex_dump=hex_dump), number=1)
                    print(t)
                    del new_image

                if True:
                    new_disk = fdimagelib.FLOPPY_DISK_D88()
                    t = timeit.timeit(lambda: new_disk.deserialize(file_name, hex_dump=hex_dump), number=1)
                    print(t)

                    fs = fdimagelib.FM_FILE_SYSTEM()
                    fs.set_image(new_disk)
                    fs.dump_valid_directory()

    def test_cmd_fmdir(self):
        subprocess.run(f'python fmdir.py -f {TestDiskImage.test_image_file} -n 0 -v', shell=True)

    def test_cmd_fmread(self):
        for index in range(30):
            subprocess.run(f'python fmread.py -f {TestDiskImage.test_image_file} -i {index} -v', shell=True)
        subprocess.run(f'python fmread.py -f {TestDiskImage.test_image_file} -i 0 -v -o test.out', shell=True)
        file_names = ('ASM09', 'ASM09EB', 'DEBUG', 'DISASM')
        for file_name in file_names:
            subprocess.run(f'python fmread.py -f {TestDiskImage.test_image_file} -t {file_name} -v', shell=True)

# ===================================================================


test_set = [
    'test_file_load',
    'test_image_access',
    'test_basic_ir_decoding',
    'test_create_new_image',
    'test_create_new_file',
    'test_delete_file',
    'test_basic_image_access',
    'test_write_image',
    'test_serialize_deserialize',
    'test_read_file_by_idx',
    'test_get_directory_entries',
    'test_cmd_fmdir',
    'test_cmd_fmread'
]
match 0:
    case 0:
        unittest.main()
    case 1:
        unittest.main(TestDiskImage, defaultTest=test_set)
    case 2:
        test_num = 12
        print(test_set[test_num])
        unittest.main(TestDiskImage, defaultTest=test_set[test_num])
    case _:
        pass

