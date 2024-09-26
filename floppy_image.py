import os
import struct
import math

import base64
import yaml
import json

class FLOPPY_IMAGE_D88:
    def __init__(self):
        self.image_data = None
        self.images = []
        self.d88_max_track = 164

    def read_file(self, file_name):
        if not os.path.isfile(file_name):
            raise FileNotFoundError
        with open(file_name, 'rb') as f:
            self.image_data = f.read()
        self.parse_image()

    def write_file(self, file_name):
        if self.image_data == None:
            return
        self.prepare_image_data()
        with open(file_name, 'wb') as f:
            f.write(self.image_data)

    def prepare_image_data(self):
        raise NotImplementedError

    def parse_sectors(self, track_data):
        """
        Parse given track image data and extracts sectors.
        """
        curr_pos = 0
        sect_idx = 0
        sectors = []
        while curr_pos < len(track_data):
            sect_header = struct.unpack_from('<BBBBHBBB5xH', track_data, curr_pos)
            C, H, R, N = sect_header[:4]
            num_sectors = sect_header[4]                # number of sectors in the track
            density = sect_header[5]                    # 0x00:double, 0x40:single
            data_mark = sect_header[6]                  # 0x00:normal, 0x10:deleted
            status = sect_header[7]                     # 0x00:no error, 0x10:no error(DDM), 0xa0:ID CRC error, 0xb0:Data CRC error, 0xe0:no address mark, 0xf0:no data mark 
            data_size = sect_header[8]
            curr_pos += 0x10                            # skip the header
            sect_data = track_data[curr_pos: curr_pos+data_size]
            curr_pos += data_size
            res = { 'sect_idx': sect_idx }
            res.update({'C':C, 'H':H, 'R':R, 'N':N })
            res.update({'num_sectors': num_sectors})
            res.update({'density': density})
            res.update({'data_mark': data_mark})
            res.update({'status': status})
            res.update({'data_size': data_size})
            res.update({'sect_data': sect_data})
            sect_idx += 1
            sectors.append(res)
        return sectors

    def parse_image(self):
        image_pos = 0
        total_image_size = len(self.image_data)
        while image_pos < total_image_size:
            d88header = struct.unpack_from(f'<17s9xBBI{self.d88_max_track}I', self.image_data, 0)
            disk_name, write_protect, disk_type, disk_size = d88header[:4]
            track_table = d88header[4:]
            image_data = self.image_data[image_pos : image_pos + disk_size + 1]
            disk_image = FLOPPY_DISK_D88()
            disk_image.set_meta_data(disk_name = disk_name,
                                      write_protect = write_protect,
                                      disk_type = disk_type)
            for track in range(self.d88_max_track):        # D88 image max track num == 163
                track_ofst = track_table[track]
                if track_ofst != 0:
                    if track < 163:
                        track_end = track_table[track + 1]
                    else:
                        track_end = disk_size
                    track_size = track_end - track_ofst
                    track_data = image_data[track_ofst : track_end]
                else:
                    track_size = 0
                    track_data = []

                sectors = self.parse_sectors(track_data)
                disk_image.tracks[track] = sectors
            
            self.images.append(disk_image)
            image_pos += disk_size 
 
    def create_add_new_empty_image(self):
        new_image = FLOPPY_DISK_D88()
        new_image.create_new_disk()
        self.images.append(new_image)



class FLOPPY_DISK_D88:
    def __init__(self):
        self.image_data = None
        self.optional_args = {}
        self.sect_per_track = 16
        self.d88_max_track = 164
        self.tracks = [[] for _ in range(self.d88_max_track)]

    def set_meta_data(self, disk_name, write_protect, disk_type):
        self.disk_name = disk_name
        self.write_protect = write_protect
        self.disk_type = disk_type

    def read_sector(self, track, sect_id, ignoreCH = True):
        """
        Read a sector. Use track number and sector ID (C, H, R) to specify the sector.  
        Input parameters:  
          track = Track number (0-163)  
          sect_id = (C, H, R). Use sect_idx instead of sect_id when None is set.  
          ignoreCH = Ignores C and H parameters and cares only R  
        """
        if track < 0 or track >= len(self.tracks):
            raise ValueError
        C, H, R = sect_id
        for sect in self.tracks[track]:
            match = False
            if ignoreCH:
                if sect['R'] == R:
                    match = True
            else:
                if sect['C'] == C and sect['H'] == H and sect['R'] == R:
                    match = True
            if match:
                return sect
        return None

    def read_sector_LBA(self, LBA):
        """
        Read a sector. Use LBA to specify the sector. LBA starts from 0 and LBA=0 represents the CHR=(0,0,1)
        """
        track = LBA // self.sect_per_track
        C = track // 2
        H = track % 2
        R = LBA % self.sect_per_track + 1
        return self.read_sector(track, (C, H, R), True)

    def read_sector_idx(self, track, sect_idx):
        """
        Input parameters:
          track = Track number (0-163)
          sect_idx = The sector index is counted from the top of the track starts with 0. Use sect_id instead of sect_idx when None is set.
        """
        if track < 0 or track >= len(self.tracks):
            raise ValueError
        track_data = self.tracks[track]
        num_sectors = track_data[0]['num_sectors']       # obtain number of sectors in the track from the 1st sector data
        if sect_idx < num_sectors:
            sect = track_data[sect_idx]
            return sect
        return None

    def adjust_num_sectors(self, track):
        """
        Adjust the number of sectors parameter
        """
        num_sectors = len(track)
        for sect in track:
            sect['num_sectors'] = num_sectors

    def renumber_sect_idx(self, track):
        for idx, sect in enumerate(track):
            sect['sect_idx'] = idx

    def write_sector(self, track, sect_id = None, write_data=None, density=0x00, data_mark=0x00, status=0x00, ignoreCH = True, create_new=False):
        """
        Write data to a sector. Use track number and sector ID (C, H, R) to specify the sector.  
        Input parameters:  
          track = Track number (0-163)  
          sect_id = (C, H, R). Use sect_idx instead of sect_id when None is set.  
          sect_idx = The sector index is counted from the top of the track starts with 0. Use sect_id instead of sect_idx when None is set.  
          ignoreCH = Ignores C and H parameters and cares only R  
          create_new = Create a new sector when the specified sector does not exist  
        """
        write_data = bytearray(write_data)
        sect = self.read_sector(track, sect_id, ignoreCH)
        data_size = int(math.pow(2, math.ceil(math.log(len(write_data))/math.log(2))))       # round up the data size to power of 2
        if data_size != len(write_data):
            print(f'WARNING: data size is rounded up to power of 2 ({len(write_data)} -> {data_size})')
            write_data.extend(bytearray(data_size - len(write_data)))
        if sect is not None:
            #sect['sect_idx'] = x       # no change
            sect['sect_data'] = write_data
            sect['data_size'] = len(write_data)
            sect['status'] = status
            sect['data_mark'] = data_mark
            sect['density'] = density
            #sect['num_sectors']        # no change
            assert id(sect) == id(self.tracks[track][sect['sect_idx']])
        elif create_new:
            C, H, R = sect_id
            N = int(math.log(len(write_data))/math.log(2))-7
            new_sector = {
                'sect_idx': len(self.tracks),
                'C': C,
                'H': H,
                'R': R,
                'N': N,
                'num_sectors': 1,           # dummy
                'density': density,
                'data_mark': data_mark,
                'status': status,
                'data_size': len(write_data),
                'sect_data': write_data
            }
            self.tracks[track].append(new_sector)
            self.adjust_num_sectors(self.tracks[track])
            self.renumber_sect_idx(self.tracks[track])

    def write_sector_LBA(self, LBA, write_data=None, density=0x00, data_mark=0x00, status=0x00, create_new=False):
        """
        Write data to a sector. Use LBA to specify the sector. LBA starts from 0 and LBA=0 represents the CHR=(0,0,1)
        """
        track = LBA // self.sect_per_track
        C = track // 2
        H = track % 2
        R = LBA % self.sect_per_track + 1
        self.write_sector(track, (C, H, R), write_data, density, data_mark, status, True, create_new)

    def write_sector_idx(self, track, sect_idx = None, write_data=None, density=0x00, data_mark=0x00, status=0x00):
        """
        Input parameters:  
          track = Track number (0-163)  
          sect_idx = The sector index is counted from the top of the track starts with 0. Use sect_id instead of sect_idx when None is set.
        """
        write_data = bytearray(write_data)
        sect = self.read_sector_idx(track, sect_idx)
        data_size = int(math.pow(2, math.ceil(math.log(len(write_data))/math.log(2))))       # round up the data size to power of 2
        if data_size != len(write_data):
            print(f'WARNING: data size is rounded up to power of 2 ({len(write_data)} -> {data_size})')
            write_data.extend(bytearray(data_size - len(write_data)))
        if sect is not None:
            #sect['sect_idx'] = x       # no change
            sect['sect_data'] = write_data
            sect['data_size'] = len(write_data)
            sect['status'] = status
            sect['data_mark'] = data_mark
            sect['density'] = density
            #sect['num_sectors']        # no change
            assert id(sect) == id(self.tracks[track][sect['sect_idx']])

    def encode_to_hex(self, data):
        res = ''
        for dt in data:
            res += f'{dt:02x} '
        if res != '':
            res = res[:-1]
        return res

    def create_new_sector(self, C, H, R, N, status, data_mark, density, sect_idx=-1, num_sectors=-1):
            sect_data_size = 2 ** (7+N)
            sect_data = bytearray([0x00] * sect_data_size)
            sect = {
                'sect_idx': sect_idx,
                'C': C,
                'H': H,
                'R': R,
                'N': N,
                'sect_data': sect_data,
                'data_size': sect_data_size,
                'status': status,
                'data_mark': data_mark,
                'density': density,
                'num_sectors': num_sectors
            }
            return sect

    def create_new_track(self, C, H):
        track = []
        for R in range(1, 16+1):
            sect = self.create_new_sector(C, H, R, 1, status=0x00, data_mark=0x00, density=0x00)
            track.append(sect)
        self.adjust_num_sectors(track)
        self.renumber_sect_idx(track)
        return track

    def create_new_disk(self, max_valid_track_num = 79):
        tracks = []
        for track_num in range(self.d88_max_track):
            if track_num <= max_valid_track_num:
                C = track_num // 2
                H = track_num % 2
                new_track = self.create_new_track(C, H)
            else:
                new_track = []          # No sector
            tracks.append(new_track)
        self.tracks = tracks
        return tracks

    def serialize(self, format='yaml', hex_dump=False):
        tracks_copy = self.tracks.copy()
        # Encode sector data
        for track in tracks_copy:
            for sect in track:
                if hex_dump:
                    sect['sect_data'] = self.encode_to_hex(sect['sect_data'])
                else:
                    sect['sect_data'] = base64.b64encode(sect['sect_data']).decode()
        match format:
            case 'json' | 'JSON':
                return json.dumps(tracks_copy, indent=4)
            case 'yaml' | 'YAML':
                return yaml.dump_all(self.tracks)
            case _:
                raise ValueError
