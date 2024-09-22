from floppy_image import *
from file_system import *

image_file = FLOPPY_IMAGE_D88()
#image.read_file('fb_toolbox.d77')
image_file.read_file('Expert FM.D77')

disk_image = image_file.images[0]

if False:
    print(disk_image.read_sector(0, (0,0,1)))

    disk_image.write_sector(0, None, 15, write_data = bytearray(256), create_new=True)
    print(disk_image.read_sector(0, (0,0,0x11)))

fs = FM_FILE_SYSTEM()
fs.set_image(disk_image)
if True:
    files = fs.list_files()
    print(files)

print(fs.read_FAT())
print(fs.image.read_sector(2, (1,0,4)))

print()
data = fs.read_file('pﾏｲｸﾉﾀﾋ゛')
print(asciij_to_utf8(data))
print(len(data))