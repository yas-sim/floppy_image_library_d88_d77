import os
import argparse

import fdimagelib

def main(args):
    image_file, disk_image = fdimagelib.open_image(args.file, '0')
    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)

    path, file_name = os.path.split(args.source)
    base, ext = os.path.splitext(file_name)
    adjusted_source_name = os.path.join(path, f'{base:8}{ext}')

    if not os.path.exists(adjusted_source_name):
        raise FileNotFoundError(f'Source file does not found ({adjusted_source_name})')
    with open(adjusted_source_name, 'rb') as f:
        data = f.read()

    file_type, ascii_flag, random_access_flag = fdimagelib.string_to_attributes(ext[1:])    # [1:] exclude '.' on the top of the extension name
    fs.write_file(base, data, file_type, ascii_flag, random_access_flag, overwrite=True)
    image_file.write_file(args.file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmwrite', 'Write a file to a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('-s', '--source', required=True, help='Source file name to be written to the image file.')
    #parser.add_argument('-d', '--destination', required=True, help='Destination file name in the image file')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
