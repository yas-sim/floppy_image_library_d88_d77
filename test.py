from floppy_image import *
from file_system import *

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
    files = fs.list_files()
    print(files)

#print(fs.read_FAT())
#print(fs.image.read_sector(2, (1,0,4)))

print()
data = fs.read_file('EXMON.M')
#print(data)
data = fs.file_decode(data['data'], data['file_type'], data['ascii_flag'])
print(data)