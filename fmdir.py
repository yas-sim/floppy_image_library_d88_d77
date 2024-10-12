import os
import argparse

import fdimagelib

def main(args):
    image_file, disk_image = fdimagelib.open_image(args.file, args.image_number)

    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)
    entries = fs.get_valid_directory_entries()
    for entry in entries:
        entry['random_access_flag'] = 'S' if entry['random_access_flag']==0x00 else 'R' if entry['random_access_flag']==0xff else '?'
        entry['ascii_flag'] = 'B' if entry['ascii_flag']==0x00 else 'A' if entry['ascii_flag']==0xff else '?'
        if args.original == False:
            print('{dir_idx:3d} {file_name_j:8} {file_type:1} {ascii_flag:1} {random_access_flag:1} {top_cluster:3d} {num_sectors:4d}'.format(**entry))
        else:
            print('{dir_idx:3d} {file_name} {file_name_j:8} {file_type:1} {ascii_flag:1} {random_access_flag:1} {top_cluster:3d} {num_sectors:4d}'.format(**entry))
    num_free_clusters = fs.get_number_of_free_clusters()
    if args.verbose:
        print(f'{num_free_clusters} Clusters Free')

if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmdir', 'Display directory of a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('--original', required=False, default=False, action='store_true', help='Display the original file name')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
