import os
import argparse

import base64
import yaml
import json

import fdimagelib

def main(args):
    image_file, disk_image = fdimagelib.open_image(args.file, args.image_number)
    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)

    if args.source != '' and args.source is not None:
        if not fs.is_exist(args.source):
            raise FileNotFoundError(f'Target file does not exist. ({args.source})')
        data = fs.read_file(args.source)
    elif args.index != '' and args.index is not None:
        data = fs.read_file_by_idx(int(args.index))
        if len(data['file_name']) == 0:
            raise FileNotFoundError(f'Target file does not exist. (index=={args.index})')
    else:
        raise ValueError('Either one of --source or --index must be specified.')
    if args.verbose:
        print(f"Read file: {data['file_name_j']}")

    extracted_contents = fs.extract_file_contents(data['data'], data['file_type'], data['ascii_flag'])
    default_attr_str = ''.join(fdimagelib.attributes_to_string(data['file_type'], data['ascii_flag'], data['random_access_flag']))  # "2BS", "0BS", ...

    match extracted_contents['file_type']:
        case 0:                                             # BASIC IR
            if args.decode_ir == True:
                write_data = fdimagelib.F_BASIC_IR_decode(extracted_contents['data'])
                write_data = write_data.encode()
                attr_str = 'txt'
            else:
                write_data = extracted_contents['data']
                attr_str = default_attr_str
        case 2:
            entry_address = extracted_contents['entry_address']
            top_address = extracted_contents['load_address']
            file_contents = extracted_contents['data'][5:-6]                                        # Exclude header and footer, and extract the binary contents
            if args.srecord:
                motorolas = fdimagelib.MOTOROLA_S()
                motorolas.set_entry_address(entry_address)
                for ofst, dt in enumerate(file_contents):
                    motorolas.add_data(top_address + ofst, dt)
                write_data = motorolas.encode().encode()
                attr_str = 'mot'
            elif args.yaml or args.json:
                if args.yaml:
                    write_data = yaml.dump(extracted_contents)
                    write_data = write_data.encode()
                    attr_str = 'yaml'
                else:
                    extracted_contents['data'] = base64.b64encode(extracted_contents['data']).decode()
                    write_data = json.dumps(extracted_contents, indent=4)
                    write_data = write_data.encode()
                    attr_str = 'json'
            else:
                write_data = extracted_contents['data']
                attr_str = default_attr_str
        case _:
            if data['file_type'] == 0 and data['ascii_flag'] == 0xff and data['random_access_flag'] == 0:   # BASIC source code in ASCII
                write_data = extracted_contents['data'][:-1]
                attr_str = 'txt'
            else:
                write_data = file_contents['data']
                attr_str = default_attr_str


    if args.destination != '' and args.destination is not None:
        destination_file = f"{args.destination}.{attr_str}"
    else:                                                           # destination file name is not specified. Use "input file name" as file name. 
        destination_file = f"{data['file_name_j']}.{attr_str}"      # Use input file attributes (e.g. "0BS") as the file extension

    with open(destination_file, 'wb') as f:
        f.write(write_data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmread', 'Read a file from a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('-s', '--source', required=False, help='Source file name in the image file to read.')
    parser.add_argument('-i', '--index', required=False, help='Directory index number to specify the target file to read.')
    parser.add_argument('-d', '--destination', required=False, help='Destination (destination) file name. When omitted, the source file name and file attributes are used to generate the destination file name.')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    parser.add_argument('--decode_basic', required=False, action='store_true', default=False, help='Decode BASIC IR code and store it as a plain text file.')
    parser.add_argument('--srecord', required=False, action='store_true', default=False, help='Convert a machine code file contents to Motorola S-record format.')
    parser.add_argument('--yaml', required=False, action='store_true', default=False, help='Convert a machine code file contents to YAML format.')
    parser.add_argument('--json', required=False, action='store_true', default=False, help='Convert a machine code file contents to JSON format.')
    args = parser.parse_args()
    main(args)
