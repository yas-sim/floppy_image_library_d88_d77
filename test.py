from floppy_image import *

image_file = FLOPPY_IMAGE_D88()
#image.read_file('fb_toolbox.d77')
image_file.read_file('Expert FM.D77')

disk_image = image_file.images[0]

print(disk_image.read_sector(0, (0,0,1)))

disk_image.write_sector(0, None, 15, write_data = bytearray(256), create_new=True)
print(disk_image.read_sector(0, (0,0,0x11)))
