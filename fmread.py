import os
import argparse

import fdimagelib

def add_attribute_to_file_name(file_name, file_type:int, ascii_flag:int, random_access_flag:0):
    res  = str(file_type)
    res += 'B' if ascii_flag == 0x00 else 'A' if ascii_flag==0xff else '-'
    res += ''

def main(args):
    image_file, disk_image = fdimagelib.open_image(args.file, args.image_number)
    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)

    if args.target_file != '' and args.target_file is not None:
        target_file = args.target_file
        if not fs.is_exist(args.target_file):
            raise FileNotFoundError(f'Target file is not existing ({args.target_file})')
        data = fs.read_file(args.target_file)
    elif args.index != '' and args.index is not None:
        data = fs.read_file_by_idx(int(args.index))
        if len(data['file_name']) == 0:
            raise FileNotFoundError(f'Target file is not existing. (index=={args.index})')
    else:
        raise ValueError('Either one of --target_file or --index must be specified.')
    if args.verbose:
        print(f"Read file: {data['file_name_j']}")

    attr_str = fdimagelib.attributes_to_string(data['file_type'], data['ascii_flag'], data['random_access_flag'])
    if args.output != '' and args.output is not None:
        root, ext = os.path.splitext(args.output)
        output_file = f"{root}-{''.join(attr_str)}{ext}"
    else:                                                           # Output file name is not specified. Use "input file name" as file name. 
        output_file = f"{data['file_name_j']}.{''.join(attr_str)}"  # Use input file attributes (e.g. "2B0") as the file extension
    with open(output_file, 'wb') as f:
        f.write(data['data'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmdir', 'Read a file from a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('-t', '--target_file', required=False, help='Target file name in the image file to read.')
    parser.add_argument('-i', '--index', required=False, help='Directory index number to specify the target file to read.')
    #parser.add_argument('--original', required=False, default=False, action='store_true', help='Display original file name')
    parser.add_argument('-o', '--output', required=False, help='Output file name. When omitted, the input file name and file attributes are used to generate the output file name.')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
