import os
import argparse

import fdimagelib

def main(args):
    if args.file == '':
        return
    if os.path.exists(args.file) == False:
        raise FileNotFoundError
    image_file = fdimagelib.FLOPPY_IMAGE_D88()
    image_file.read_file(args.file)

    num_images = len(image_file.images)
    if args.verbose:
        print(f'{num_images} images detected.')
    image_number = int(args.image_number)
    if image_number >= num_images:
        raise ValueError
    disk_image = image_file.images[image_number]

    fs = fdimagelib.FM_FILE_SYSTEM()
    fs.set_image(disk_image)
    entries = fs.get_valid_directory_entries()
    for entry in entries:
        if args.original == False:
            print('{dir_idx:3d} {file_name_j:8} {file_type:1d} {ascii_flag:3d} {random_access_flag:3d} {top_cluster:3d} {num_sectors:4d}'.format(**entry))
        else:
            print('{dir_idx:3d} {file_name} {file_name_j:8} {file_type:1d} {ascii_flag:3d} {random_access_flag:3d} {top_cluster:3d} {num_sectors:4d}'.format(**entry))
    num_free_clusters = fs.get_number_of_free_clusters()
    if args.verbose:
        print(f'{num_free_clusters} Clusters Free')

if __name__ == '__main__':
    parser = argparse.ArgumentParser('fmdir', 'Displays directory of a D88/D77 image file')
    parser.add_argument('-f', '--file', required=True, help='D88/D77 image file name')
    parser.add_argument('-n', '--image_number', required=False, default=0, help='Specify target image number (if the image file contains multiple images). Default=0')
    parser.add_argument('-o', '--original', required=False, default=False, action='store_true', help='Display original file name')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbose flag')
    args = parser.parse_args()
    main(args)
