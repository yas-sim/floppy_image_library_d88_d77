import unittest

from floppy_image import *
from file_system import *
from fbasic_utils import *

from misc import *

def create_new_image():
    new_image = FLOPPY_IMAGE_D88()
    new_image.create_and_add_new_empty_image()
    new_disk = new_image.images[0]
    fs = FM_FILE_SYSTEM()
    fs.set_image(new_disk)
    fs.logical_format()
    return new_image


class TestDiskImage(unittest.TestCase):
    test_image_file = 'fb_toolbox.d77'

    def test_file_load(self):
        image_file = FLOPPY_IMAGE_D88()
        image_file.read_file(TestDiskImage.test_image_file)

        disk_image = image_file.images[0]

        fs = FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        fs.dump_valid_directory()
        fs.dump_FAT()

    def test_image_access(self):
        image_file = FLOPPY_IMAGE_D88()
        image_file.read_file(TestDiskImage.test_image_file)


    def test_basic_ir_decoding(self):
        image_file = FLOPPY_IMAGE_D88()
        image_file.read_file('fb_toolbox.d77')

        disk_image = image_file.images[0]

        fs = FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        fs.dump_valid_directory()
        fs.dump_FAT()

        data = fs.read_file('ASM09')
        basic_ir = fs.extract_file_contents(data['data'], data['file_type'], data['ascii_flag'])
        basic_text = F_BASIC_IR_decode(basic_ir['data'])
        print()
        print(basic_text)

    def test_create_new_image(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        fs = FM_FILE_SYSTEM()
        fs.set_image(new_disk)
        fs.logical_format()
        print(fs.check_disk_id())
        print(fs.image.read_sector_LBA(2))
        fs.dump_valid_directory()
        fs.dump_FAT()

    def test_create_new_file(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]

        fs = FM_FILE_SYSTEM()
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

        fs = FM_FILE_SYSTEM()
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

    def test_serialize_image(self):
        new_image = create_new_image()
        new_disk = new_image.images[0]
        serialized_data = new_disk.serialize('yaml', hex_dump=True)
        #print(serialized_data)

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
        image_file = FLOPPY_IMAGE_D88()
        image_file.read_file('fb_toolbox.d77')

        disk_image = image_file.images[0]

        fs = FM_FILE_SYSTEM()
        fs.set_image(disk_image)
        data = fs.read_file('ASM09EB')
        print("data", len(data['data']))
        fs.dump_FAT()
        fs.write_file('ASM09CP', data['data'], data['file_type'], data['ascii_flag'], data['random_access_flag'])
        fs.dump_valid_directory()
        image_file.write_file('test.d77')
        fs.dump_FAT()

unittest.main()
