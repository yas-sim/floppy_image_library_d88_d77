from floppy_image import *
from file_system import *
from misc import *

image_file = FLOPPY_IMAGE_D88()
#image.read_file('fb_toolbox.d77')
#image_file.read_file('Expert FM.D77')
image_file.read_file('cdos7v2.d77')

disk_image = image_file.images[0]

if False:
    print(disk_image.read_sector(0, (0,0,1)))

    disk_image.write_sector(0, None, 15, write_data = bytearray(256), create_new=True)
    print(disk_image.read_sector(0, (0,0,0x11)))

fs = FM_FILE_SYSTEM()
fs.set_image(disk_image)
if True:
   #fs.dump_directory()
   fs.dump_valid_directory()
   fs.dump_FAT()

#print(fs.read_FAT())
#print(fs.image.read_sector(2, (1,0,4)))

data = fs.read_file('EXMON')
print()
print(data)

data = fs.extract_file_contents(data['data'], data['file_type'], data['ascii_flag'])
print('\ncontents')
print(data)

from fbasic_utils import *

basic_text = F_BASIC_IR_decode(data['data'])
print()
print(basic_text)

fs.dump_valid_directory()
fs.dump_FAT()

#print(fs.find_empty_directory_slot())
#print(fs.get_directory_entry_idx('XFER'))

fs.delete_file('XFER')
fs.dump_valid_directory()
fs.dump_FAT()

#fs.create_directory_entry(fs.normalize_file_name('SHIMURA'), 0, 0, 0)
#fs.dump_valid_directory()

dummy = bytearray([0x02 for _ in range(19700)])
fs.write_file('SHIMURA', dummy, 0, 0, 0)
fs.dump_valid_directory()
fs.dump_FAT()

if False:
    serialized_data = disk_image.serialize('json')
    print(serialized_data)

#new_disk = FLOPPY_DISK_D88()
#new_disk.create_new_disk()

new_image = FLOPPY_IMAGE_D88()
new_image.create_add_new_empty_image()
new_disk = new_image.images[0]
print(new_disk.read_sector_LBA(16))
fs.set_image(new_disk)
fs.logical_format()
print(fs.check_disk_id())
print(fs.image.read_sector_LBA(2))
fs.dump_valid_directory()
fs.write_file('TESTFILE', dummy, 0, 0, 0)
fs.dump_valid_directory()
fs.dump_FAT()

fat = fs.read_FAT()
dump_data(fat)
print()

data = disk_image.read_sector_LBA(2)['sect_data']
dump_data(data)
