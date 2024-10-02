import os
import argparse

import fdimagelib

def main(args):
    image_file = fdimagelib.FLOPPY_IMAGE_D88()
    image_file.create_and_add_new_empty_image()
    disk_image = image_file.images[0]

    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)
    fs.logical_format()
    image_file.write_file(args.file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmmakedisk', 'Create a new D88/D77 image file with logical format.')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
