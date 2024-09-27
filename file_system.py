from floppy_image import *
from ascii_j import *
from misc import *


class FM_FILE_SYSTEM:
    def __init__(self):
        self.sect_per_cluster = 8
        self.sect_per_track = 16
        self.max_cluster_num = 151
        self.image = None

    def set_image(self, image:FLOPPY_DISK_D88):
        self.image = image

    def check_disk_id(self):
        id_sect = self.image.read_sector(0, (0, 0, 3))
        dump_data(id_sect['sect_data'])
        if id_sect['sect_data'][0] != ord('S'):
            return False
        return True



    def CHR_to_LBA(self, C, H, R):
        LBA = (C * 2 + H) * self.sect_per_track + R - 1
        return LBA

    def LBA_to_CHR(self, LBA):
        track = LBA // self.sect_per_track
        sect = LBA % self.sect_per_track
        C = track // 2
        H = track % 2
        R = sect
        return (C, H, R)

    def CHR_to_cluster(self, C, H, R):
        if C < 2:
            return -1
        LBA = self.CHR_to_LBA(C, H, R)
        cluster = self.LBA_to_cluster(LBA)
        return cluster

    def LBA_to_cluster(self, LBA):
        # Cluster number starts from track 4 (not track 0).
        if LBA < self.sect_per_track * 4:
            return -1
        cluster = (LBA - self.sect_per_track * 4) // self.sect_per_cluster        
        return cluster

    def cluster_to_LBA(self, cluster):
        LBA = self.sect_per_track * 4 + cluster * self.sect_per_cluster
        return LBA

    def cluster_to_CHR(self, cluster):
        sect_idx = self.cluster_to_LBA(cluster)
        C, H, R = self.LBA_to_CHR(sect_idx)
        return (C, H, R)



    def read_FAT(self):
        FAT = self.image.read_sector(2, (1, 0, 1))['sect_data']
        return bytearray(FAT)

    def write_FAT(self, FAT_data):
        self.image.write_sector(2, (1, 0, 1), FAT_data)

    def trace_FAT_chain(self, start_cluster):
        """
        Input parameters:
          start_cluster
        """
        chain = []
        FAT = self.read_FAT()
        curr_cluster = start_cluster
        while True:
            chain.append(curr_cluster)
            next_cluster = FAT[5 + curr_cluster]                # FAT starts from 6th byte
            if next_cluster <= 0x97:   # 0x97 == 151 == self.max_cluster_num
                curr_cluster = next_cluster
            elif next_cluster >= 0xc0 and next_cluster <= 0xc7:
                used_sectors_in_last_cluster = (next_cluster & 0x0f) + 1
                return (chain, used_sectors_in_last_cluster)
            elif next_cluster == 0xfd:
                used_sectors_in_last_cluster = 0                # No sectors are used in this cluster
                return (chain, used_sectors_in_last_cluster)
            elif next_cluster == 0xfe:
                return ([], -1)                                 # This cluster is reserved for system use
            elif next_cluster == 0xff:
                return ([], -1)                                 # This cluster is free (not used)

    def delete_FAT_chain(self, chain:list[int]):
        FAT = bytearray(self.read_FAT())
        for ch in chain[0]:
            if ch <= self.max_cluster_num:
                FAT[ch + 5] = 0xff
        self.write_FAT(FAT)

    def find_empty_cluster(self):
        """
        Return:
          An empty cluster number. -1 when no empty cluster is found.
        """
        FAT = self.read_FAT()
        for cluster in range(self.max_cluster_num + 1):
            if FAT[cluster + 5] == 0xff:
                return cluster
        return -1

    def get_number_of_free_clusters(self):
        FAT = self.read_FAT()
        count = 0
        ofst = 5
        for pos in range(self.max_cluster_num+1):
            if FAT[pos + ofst] == 0xff:
                count += 1
        return count

    def get_all_directory_entries(self):
        """
        Return:
          [{'file_name':, 'file_name_j':, 'file_type':, 
          'ascii_flag':, 'random_access_flag':, 
          'top_cluster':, 'num_sectors':, 'dir_idx': }]
        """
        files = []
        directory_start_sector = self.CHR_to_LBA(1, 0, 4)
        dir_idx = 0
        for sect_ofst in range(32-4):
            LBA = directory_start_sector + sect_ofst
            data = self.image.read_sector_LBA(LBA)
            sect_data = data['sect_data']
            # 1 directory entry = 32 bytes
            for idx in range(256//32):
                entry = struct.unpack_from('<8s3xBBBB', sect_data, idx * 32)
                file_name, file_type, ascii_flag, random_access_flag, top_cluster = entry
                file_name_j = asciij_to_utf8(file_name)
                if top_cluster >=0 and top_cluster <= self.max_cluster_num:
                    FAT_chain, last_secs = self.trace_FAT_chain(top_cluster)
                    num_sectors = (len(FAT_chain)-1) * self.sect_per_cluster + last_secs
                else:
                    FAT_chain, last_secs = [], 0
                    num_sectors = 0
                res = { 'file_name':file_name, 'file_name_j':file_name_j, 'file_type':file_type, 'ascii_flag':ascii_flag, 'random_access_flag':random_access_flag, 'top_cluster':top_cluster, 'num_sectors':num_sectors, 'dir_idx':dir_idx }
                files.append(res)
                dir_idx += 1
        return files

    def get_valid_directory_entries(self):
        """
        Return:
          [{'file_name':, 'file_name_j':, 'file_type':, 
          'ascii_flag':, 'random_access_flag':, 
          'top_cluster':, 'num_sectors':, 'dir_idx': }]
        """
        valid_entries = []
        dir_entries = self.get_all_directory_entries()
        for dir_entry in dir_entries:
            if dir_entry['file_name'][0] == 0x00:        # Deleted entry
                continue
            if dir_entry['file_name'][0] == 0xff:
                continue                    # ever used ?
            if dir_entry['file_type'] not in (0, 1, 2) or dir_entry['ascii_flag'] not in (0, 0xff) or dir_entry['random_access_flag'] not in (0, 0xff) or dir_entry['top_cluster'] > self.max_cluster_num:
                continue
            valid_entries.append(dir_entry)
        return valid_entries

    def get_directory_entry(self, file_name:str):
        """
        Return:
          {'file_name':, 'file_name_j':, 'file_type':, 
          'ascii_flag':, 'random_access_flag':, 
          'top_cluster':, 'num_sectors':, 'dir_idx': }
        """
        dir_entries = self.get_valid_directory_entries()
        for dir_entry in dir_entries:
            match = self.compare_file_names(dir_entry['file_name'], file_name)
            if match:
                return dir_entry
        return {'file_name':'', 'file_name_j':'', 'file_type':-1, 'ascii_flag':-1, 'random_access_flag':-1, 'top_cluster':-1, 'num_sectors=':-1, 'dir_idx':-1}


    def normalize_file_name(self, file_name:any):
        """
        Return:
        """
        if type(file_name) is bytes:
            file_name = bytearray(file_name)
        elif type(file_name) is str:
            file_name = bytearray(file_name.encode())
        if type(file_name) != bytearray:
            raise TypeError
        if len(file_name) < 8:
            file_name.extend([ord(' ') for _ in range(8-len(file_name))])
        return file_name


    def compare_file_names(self, file_name1:str | bytearray, file_name2:str | bytearray):
        file_name1 = self.normalize_file_name(file_name1)
        file_name2 = self.normalize_file_name(file_name2)
        if file_name1 == file_name2:
            return True
        return False



    def get_directory_entry_idx(self, file_name:str):
        """
        Return:
          The index of directory entry (starts with 0). -1 when there was no empty directory entry.
        """
        dir_entries = self.get_valid_directory_entries()
        #file_name_j = bytearray(asciij_string_to_utf8(file_name).encode())
        for dir_entry in dir_entries:
            for ofst in range(0, 256, 32):
                match = self.compare_file_names(dir_entry['file_name'], file_name)
                if match:
                    return dir_entry['dir_idx']
        return -1

    def find_empty_directory_slot(self):
        """
        Return:
          The index of empty directory entry (starts with 0). -1 when there was no empty directory entry.
        """
        dir_top_LBA = 2 * self.sect_per_track + 3
        dir_end_LBA = 3 * self.sect_per_track + self.sect_per_track -1
        dir_entry_idx = 0
        for sect_LBA in range(dir_top_LBA, dir_end_LBA+1):
            sect = self.image.read_sector_LBA(sect_LBA)
            sect_data = sect['sect_data']
            for ofst in range(0, 256, 32):
                if sect_data[ofst] == 0x00 or sect_data[ofst] == 0xff:
                    return dir_entry_idx
                dir_entry_idx += 1
        return -1

    def is_exist(self, file_name:str):
        dir_entry = self.get_directory_entry(file_name)
        existence = False if dir_entry['file_name'] == '' else True
        return existence

    def read_directry_by_dir_idx(self, dir_idx):
        sect = dir_idx // (256//32)     # 8 directory entries per sector
        idx = dir_idx % (256//32)       # directory entry index in the sector        
        data = self.image.read_sector_LBA(self.sect_per_track * 2 + 3 + sect)
        return data

    def write_directry_by_dir_idx(self, dir_idx, data):
        sect = dir_idx // (256//32)     # 8 directory entries per sector
        data = self.image.write_sector_LBA(self.sect_per_track * 2 + 3 + sect, data)

    def create_directory_entry(self, file_name:bytearray, file_type:int, ascii_flag:int, random_access_flag:int, top_cluster:int):
        dir_idx = self.find_empty_directory_slot()
        idx = dir_idx % (256//32)       # directory entry index in the sector        
        data = self.read_directry_by_dir_idx(dir_idx)['sect_data']
        data = bytearray(data)
        struct.pack_into('<8s3xBBBB', data, idx * 32, file_name, file_type, ascii_flag, random_access_flag, top_cluster)
        self.write_directry_by_dir_idx(dir_idx, data)

    def delete_directory_entry(self, dir_idx:int):
        idx = dir_idx % (256//32)       # directory entry index in the sector
        data = self.read_directry_by_dir_idx(dir_idx)['sect_data']
        data = bytearray(data)
        data[idx * 32] = 0x00
        self.write_directry_by_dir_idx(dir_idx, data)

    def pad_data_to_fit_sector(self, data:bytearray):
        num_pad = 256 - len(data) % 256
        data.extend([0xff for _ in range(num_pad)])
        return data

    def read_cluster_chain(self, chain, last_secs):
        """
        chain: list of cluster numbers
        last_secs: number of sectors used in the last cluster
        """
        res = bytearray()
        if len(chain)>0:
            num_secs = [ self.sect_per_cluster for _ in range(len(chain)-1) ]
        num_secs.append(last_secs)
        for cluster, num_sec in zip(chain, num_secs):
            LBA = self.cluster_to_LBA(cluster)
            for ofst in range(num_sec):
                sect_data = self.image.read_sector_LBA(LBA + ofst)['sect_data']
                res.extend(sect_data)
        return res

    def validate_file_attributes(self, file_type, ascii_flag, random_access_flag):
        if file_type not in (0x00, 0x01, 0x02):
            return False
        if ascii_flag not in (0x00, 0xff):
            return False
        if random_access_flag not in (0x00, 0xff):
            return False
        return True

    def validate_file_name(self, file_name):
        if file_name == None:
            return False
        if type(file_name) not in (str, bytes, bytearray):
            return False
        if file_name == '' or len(file_name)>8:
            return False
        return True

    def delete_file(self, file_name:str):
        file_name = self.normalize_file_name(file_name)
        if self.is_exist(file_name) == False:
            raise FileNotFoundError
        dir_entry = self.get_directory_entry(file_name)
        fat_chain = self.trace_FAT_chain(dir_entry['top_cluster'])
        self.delete_FAT_chain(fat_chain)
        self.delete_directory_entry(dir_entry['dir_idx'])

    def read_file(self, file_name:str):
        """
        Return:
          Dict { 'data', 'file_type', 'ascii_flag', 'file_name', 'file_name_j', 'random_access_flag, 'top_cluster', 'num_sectors', 'dir_idx' }
        """
        file_name = self.normalize_file_name(file_name)
        dir_entry = self.get_directory_entry(file_name)
        assert dir_entry['file_name'] != ''                     # File not found
        chain, last_secs = self.trace_FAT_chain(dir_entry['top_cluster'])
        file_data = self.read_cluster_chain(chain, last_secs)
        res = { 'data':file_data, **dir_entry }
        return res

    def read_file_by_idx(self, dir_idx:int):
        """
        Read file using directory index number to specify the file.
        """
        dir_entries = self.get_valid_directory_entries()
        for dir_entry in dir_entries:
            if dir_entry['dir_idx'] == dir_idx:
                res = self.read_file(dir_entry['file_name'])
                return res
        res = { 'data': '', 'file_name': '' }
        return res

    def write_file(self, file_name:str, write_data:bytearray, file_type:int, ascii_flag:int, random_access_flag:int, overwrite=False):
        if self.validate_file_name(file_name) == False:
            raise ValueError
        if self.validate_file_attributes(file_type, ascii_flag, random_access_flag) == False:
            raise ValueError
        file_name = self.normalize_file_name(file_name)
        if self.is_exist(file_name):
            if overwrite:
                self.delete_file(file_name)
            else:
                raise FileExistsError
        write_data = self.pad_data_to_fit_sector(write_data)
        FAT = self.read_FAT()
        top_cluster = -1
        prev_cluster = -1
        while True:
            assert len(write_data) % 256 == 0
            self.write_FAT(FAT)                                 # Write back FAT before searching for an empty cluster
            current_cluster = self.find_empty_cluster()
            assert current_cluster != -1                        # Disk full
            if top_cluster == -1:
                top_cluster = current_cluster                   # Memorize the top cluster nunber
            if prev_cluster != -1:
                assert prev_cluster != current_cluster
                FAT[prev_cluster + 5] = current_cluster
            LBA = self.cluster_to_LBA(current_cluster)
            for sect_count in range(self.sect_per_cluster):
                self.image.write_sector_LBA(LBA, write_data[:256])
                write_data = write_data[256:]
                FAT[current_cluster + 5] = 0xc0 + sect_count
                if len(write_data) == 0:
                    break
            if sect_count < self.sect_per_cluster - 1:
                break
            prev_cluster = current_cluster
            if len(write_data) == 0:
                return
        self.write_FAT(FAT)
        self.create_directory_entry(file_name, file_type, ascii_flag, random_access_flag, top_cluster)



    def extract_file_contents(self, file_data:bytearray, file_type:int, ascii_flag:int):
        """
        Description: Extract file contents based on the file attributes.  
        file_data: Data to decode  
        file_type: 0x00:BASIC source, 0x01:BASIC data, 0x02:Machine code  
        ascii_flag: 0x00:Binary, 0xff:ASCII  
        """
        data = bytearray()
        match ascii_flag:
            case 0x00:              # Binary
                match file_type:
                    case 0x00:
                        match file_data[0]:
                            case 0xff:      # BASIC binary source (not protected)
                                unlist = struct.unpack_from('<H', file_data, 1)     # UNLIST line number
                                eof = bytearray([0x00, 0x00, 0x00, 0x1a])
                                for pos in range(3, len(file_data)-4):              # 3:Skip ID and unlist line number on the top.
                                    if file_data[pos:pos+4] == eof:
                                        data = file_data[3:pos]
                                        res = { 'file_type':0, 'data':data, 'unlist':unlist }
                                        return res
                            case 0xfe:      # BASIC binary source (protected)
                                unlist = struct.unpack_from('>H', file_data, 1)[0]     # UNLIST line number
                                eof = 0x1a
                                for pos in range(3, len(file_data)):
                                    if file_data[pos] == eof:
                                        data = file_data[3:pos]
                                        res = { 'file_type':1, 'data':data, 'unlist':unlist }
                            case _:
                                return { 'file_type':-1 }
                    case 0x01:
                        return { 'file_type':-1 }
                    case 0x02:
                        if file_data[0] == 0x00:
                            mc_len, mc_load_addr = struct.unpack_from('>HH', file_data, 1)          # Machine code length, load address
                            eof = bytearray([0xff, 0x00, 0x00])
                            data = file_data[5:5+mc_len]
                            if file_data[5+mc_len:5+mc_len+3] == eof:
                                mc_entry_addr = struct.unpack_from('>H', file_data, 5+mc_len+3)[0]  # Entry address
                                if file_data[5+mc_len+3+2] == 0x1a:
                                    res = { 'file_type':2, 'data':data, 'length':mc_len, 'load_address':mc_load_addr, 'entry_address':mc_entry_addr}
                                    return res
                        return { 'file_type':-1 }
                    case _:
                        return { 'file_type':-1 }
            case 0xff:          # ASCII
                eof = 0x1a
                for pos in range(len(file_data)):
                    if file_data[pos] == eof:
                        data = file_data[:pos]
                        res = { 'file_type':3, 'data':data }
                        return res
            case _:
                return { 'file_type':-1 }




    def logical_format(self):
        # Create IPL
        data = bytearray([0x20, 0xfe] + [0x00] * (256-2))       # BRA * == 0x20 0xFE
        self.image.write_sector_LBA(0, data)

        # Create disk ID
        data = bytearray(list('SYS'.encode()) + [0x00]*(256-3)) # 'SYS' == Disk ID
        self.image.write_sector_LBA(2, data)

        # Create FAT
        #data = bytearray([0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xfe] + [0xff] * (256-9))
        data = bytearray([0x00] + [0xff] * (256-1))
        self.write_FAT(data)        # LBA = 32

        # Create empty directory entries
        data = bytearray([0xff] * 256)
        for sect_ofst in range(32 - 3):      # 3 == FAT + reserve + reserve
            self.image.write_sector_LBA(32 + 3 + sect_ofst, data)




    def dump_directory(self):
        dir_entries = self.get_all_directory_entries()
        for dir_entry in dir_entries:
            print(dir_entry['dir_idx'], dir_entry['file_name'], dir_entry['file_name_j'], dir_entry['file_type'], dir_entry['ascii_flag'], dir_entry['random_access_flag'], dir_entry['num_sectors'], dir_entry['top_cluster'])

    def dump_valid_directory(self):
        dir_entries = self.get_all_directory_entries()
        for dir_entry in dir_entries:
            if dir_entry['file_name'][0] == 0x00 or dir_entry['file_name'][0] == 0xff:
                continue
            print(dir_entry['dir_idx'], dir_entry['file_name'], dir_entry['file_name_j'], dir_entry['file_type'], dir_entry['ascii_flag'], dir_entry['random_access_flag'], dir_entry['num_sectors'], dir_entry['top_cluster'])

    def dump_FAT(self, ofst=5):
        FAT_data = self.read_FAT()
        dump_data(FAT_data[ofst : ofst + self.max_cluster_num + 1])
