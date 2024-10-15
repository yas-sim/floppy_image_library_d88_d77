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
            if args.decode_basic == True:
                decoded_basic_text = fdimagelib.F_BASIC_IR_decode(extracted_contents['data'])
                if args.yaml:
                    write_contents = extracted_contents.copy()
                    write_contents['basic_text'] = decoded_basic_text
                    attr_str = 'yaml'
                elif args.json:
                    write_contents = extracted_contents.copy()
                    write_contents['basic_text'] = decoded_basic_text
                    write_contents['data'] = base64.b64encode(write_contents['data']).decode()
                    attr_str = 'json'
                else:
                    write_contents = decoded_basic_text.encode()            # Output as plain BASIC text
                    attr_str = 'txt'
            else:
                write_contents = extracted_contents['data']                 # Output the data without IR decoding
                attr_str = default_attr_str

        case 2:                                                             # Machine language code / binary data
            if args.yaml or args.json:
                write_contents = extracted_contents.copy()
                write_contents['num_chunks'] = len(extracted_contents['data'])
                write_contents['data'] = []
            elif args.srecord:
                write_contents = ''
            else:
                write_contents = ''

            entry_address = extracted_contents['entry_address']

            for num, chunk in enumerate(extracted_contents['data']):
                top_address, file_contents = chunk
                if args.srecord:
                    motorolas = fdimagelib.MOTOROLA_S()
                    for ofst, dt in enumerate(file_contents):
                        motorolas.add_data(top_address + ofst, dt)
                    srec_txt = motorolas.encode()
                    write_contents += srec_txt
                    attr_str = 'mot'
                elif args.yaml:
                    #write_contents[f'data_{num}'] = bytes(file_contents)
                    record = {'address': top_address, 'contents': base64.b64encode(file_contents).decode() }
                    write_contents['data'].append(record)
                    attr_str = 'yaml'
                elif args.json:
                    record = {'address': top_address, 'contents': base64.b64encode(file_contents).decode() }
                    write_contents['data'].append(record)
                    attr_str = 'json'
                else:
                    write_contents = file_contents
                    attr_str = default_attr_str

            if args.srecord:
                motorolas = fdimagelib.MOTOROLA_S()
                motorolas.set_entry_address(entry_address)
                srec = motorolas.encode()
                write_contents += srec                          # Entry address for S-record
                write_contents = write_contents.encode()
            elif args.json or args.yaml:
                write_contents['entry_address'] = entry_address

        case _:                                             # Protected BASIC IR, Random access file, etc
            if data['file_type'] == 0 and data['ascii_flag'] == 0xff and data['random_access_flag'] == 0:   # BASIC source code in ASCII
                write_contents = extracted_contents['data'][:-1]
                attr_str = 'txt'
            else:
                write_contents = extracted_contents['data']
                attr_str = default_attr_str

    match attr_str:
        case 'yaml':
            write_contents = yaml.dump(write_contents)
            write_contents = write_contents.encode()
        case 'json':
            write_contents = json.dumps(write_contents, indent=4)
            write_contents = write_contents.encode()

    if args.destination != '' and args.destination is not None:
        destination_file = f"{args.destination}.{attr_str}"
    else:                                                           # destination file name is not specified. Use "input file name" as file name. 
        destination_file = f"{data['file_name_j']}.{attr_str}"      # Use input file attributes (e.g. "0BS") as the file extension

    with open(destination_file, 'wb') as f:
        f.write(write_contents)


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
    parser.add_argument('--json', required=False, action='store_true', default=False, help='Convert a machine code file contents to JSON format.<br>Note: The \'data\' will be encoded in base64.')
    args = parser.parse_args()

    count = 0
    count = count+1 if args.srecord else count
    count = count+1 if args.yaml    else count
    count = count+1 if args.json    else count
    assert count <= 1, 'Only one of --srecord, --yaml, or --json can be set.'
    main(args)
