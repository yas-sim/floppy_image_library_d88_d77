import os
import struct
import math

import yaml

class FLOPPY_IMAGE_D88:
    def __init__(self):
        self.image_data = None
        self.images = []

    def read_file(self, file_name):
        if not os.path.isfile(file_name):
            raise FileNotFoundError
        self.image_data = open(file_name, 'rb').read()
        self.parse_image()

    def write_file(self, file_name):
        if self.image_data == None:
            return
        open(file_name, 'wb').write(self.image_data)

    def parse_image(self):
        image_pos = 0
        total_image_size = len(self.image_data)
        print(total_image_size)
        while image_pos < total_image_size:
            d88header = struct.unpack_from('<17s9xBBI164I', self.image_data, 0)
            disk_name, write_protect, disk_type, disk_size = d88header[:4]
            track_table = d88header[4:]
            image_data = self.image_data[image_pos:image_pos+disk_size+1]
            disk_image = FLOPPY_DISK_D88()
            disk_image.set_image_data(image_data,
                                      disk_name = disk_name,
                                      write_protect = write_protect,
                                      disk_type = disk_type,
                                      disk_size = disk_size,
                                      track_table = track_table)
            self.images.append(disk_image)
            image_pos += disk_size 
 




class FLOPPY_DISK_D88:
    def __init__(self):
        self.image_data = None
        self.optional_args = {}
        self.sect_per_track = 16

    def set_image_data(self, data, **kwargs):
        self.data = data
        self.optional_args = kwargs
        self.parse()

    def parse(self):
        self.tracks = []
        for track in range(164):        # D88 image max track num == 163
            track_ofst = self.optional_args['track_table'][track]
            if track_ofst != 0:
                if track < 163:
                    track_end = self.optional_args['track_table'][track+1]
                else:
                    track_end = self.optional_args['disk_size']
                track_size = track_end - track_ofst
                track_data = self.data[track_ofst:track_end]
            else:
                track_size = 0
                track_data = []
            self.tracks.append({'track_size':track_size, 'track_data':track_data})
            sectors = self.parse_sectors(track_data)
            self.tracks[-1].update({'sectors':sectors})


    def parse_sectors(self, track_data):
        """
        Parse given track image data and extracts sectors.
        """
        curr_pos = 0
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
            res = { 'C':C, 'H':H, 'R':R, 'N':N }
            res.update({'num_sectors': num_sectors})
            res.update({'density': density})
            res.update({'data_mark': data_mark})
            res.update({'status': status})
            res.update({'data_size': data_size})
            res.update({'sect_data': sect_data})
            sectors.append(res)
        return sectors

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
        track_data = self.tracks[track]
        num_sectors = track_data['sectors'][0]['num_sectors']       # number of sectors in the track
        C, H, R = sect_id
        for sect in track_data['sectors']:
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
        num_sectors = track_data['sectors'][0]['num_sectors']       # number of sectors in the track
        if sect_idx < num_sectors:
            sect = track_data['sectors'][sect_idx]
            return sect
        return None

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
            sect['sect_data'] = write_data
            sect['data_size'] = len(write_data)
            sect['status'] = status
            sect['data_mark'] = data_mark
            sect['density'] = density
            #sect['num_sectors']        # no change
        elif create_new:
            C, H, R = sect_id
            N = int(math.log(len(write_data))/math.log(2))-7
            new_sector = {
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
            self.tracks[track]['sectors'].append(new_sector)
            # Adjust the number of sectors parameter
            num_sectors = len(self.tracks[track]['sectors'])
            for sect in self.tracks[track]['sectors']:
                sect['num_sectors'] = num_sectors

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
            sect['sect_data'] = write_data
            sect['data_size'] = len(write_data)
            sect['status'] = status
            sect['data_mark'] = data_mark
            sect['density'] = density
            #sect['num_sectors']        # no change

    def serialize(self):
        