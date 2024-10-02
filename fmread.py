import os
import argparse

import fdimagelib

def main(args):
    image_file, disk_image = fdimagelib.open_image(args.file, args.image_number)
    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)

    if args.source != '' and args.source is not None:
        if not fs.is_exist(args.source):
            raise FileNotFoundError(f'Target file is not existing ({args.source})')
        data = fs.read_file(args.source)
    elif args.index != '' and args.index is not None:
        data = fs.read_file_by_idx(int(args.index))
        if len(data['file_name']) == 0:
            raise FileNotFoundError(f'Target file is not existing. (index=={args.index})')
    else:
        raise ValueError('Either one of --source or --index must be specified.')
    if args.verbose:
        print(f"Read file: {data['file_name_j']}")

    attr_str = ''.join(fdimagelib.attributes_to_string(data['file_type'], data['ascii_flag'], data['random_access_flag']))  # "2BS", "0BS", ...
    if args.destination != '' and args.destination is not None:
        destination_file = f"{args.destination}.{attr_str}"
    else:                                                           # destination file name is not specified. Use "input file name" as file name. 
        destination_file = f"{data['file_name_j']}.{attr_str}"      # Use input file attributes (e.g. "0BS") as the file extension
    with open(destination_file, 'wb') as f:
        f.write(data['data'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmread', 'Read a file from a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('-s', '--source', required=False, help='Source file name in the image file to read.')
    parser.add_argument('-i', '--index', required=False, help='Directory index number to specify the target file to read.')
    parser.add_argument('-d', '--destination', required=False, help='Destination (destination) file name. When omitted, the source file name and file attributes are used to generate the destination file name.')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
