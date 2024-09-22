from floppy_image import *
from ascii_j import *

class FILE_SYSTEM:
    def __init__(self):
        pass


class FM_FILE_SYSTEM(FILE_SYSTEM):
    def __init__(self):
        self.sect_per_cluster = 8
        self.sect_per_track = 16
        super().__init__()

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
        return FAT

    def trace_FAT_chain(self, start_cluster):
        chain = []
        FAT = self.read_FAT()
        curr_cluster = start_cluster
        while True:
            chain.append(curr_cluster)
            next_cluster = FAT[6 + curr_cluster - 1]            # FAT starts from 6th byte
            if next_cluster < 0x97:
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

    def search_vacant_cluster(self):
        FAT = self.read_FAT()
        for cluster in range(152):
            val = FAT[6 + cluster - 1]
            if val == 0xff:
                return cluster
        return -1

    def list_files(self):
        files = []
        directory_start_sector = self.CHR_to_LBA(1, 0, 4)
        for sect_ofst in range(32-4):
            LBA = directory_start_sector + sect_ofst
            data = self.image.read_sector_LBA(LBA)
            sect_data = data['sect_data']
            # 1 directory entry = 32 bytes
            for idx in range(256//32):
                entry = struct.unpack_from('<8s3xBBBB', sect_data, idx * 32)
                file_name, file_type, ascii_flag, random_access_flag, top_cluster = entry
                if file_name[0] == 0x00:        # Deleted entry
                    continue
                if file_type not in (0, 1, 2) or ascii_flag not in (0, 0xff) or random_access_flag not in (0, 0xff) or top_cluster > 153:
                    continue
                file_name_j = asciij_to_utf8(file_name)
                FAT_chain, last_secs = self.trace_FAT_chain(top_cluster)
                num_sectors = (len(FAT_chain)-1) * self.sect_per_cluster + last_secs
                res = [ file_name, file_name_j, file_type, ascii_flag, random_access_flag, top_cluster, num_sectors]
                files.append(res)
        return files

    def check_file_name_match(self, file_name1:str, file_name2:str):
        file_name1 = file_name1.rstrip(' ')
        file_name2 = file_name2.rstrip(' ')
        if file_name1 == file_name2:
            return True
        else:
            return False

    def get_directory_entry(self, file_name:str):
        files = self.list_files()
        for file in files:
            match = self.check_file_name_match(file[1], file_name)
            if match:
                return file
        return ['','',-1,-1,-1,-1,-1]

    def read_cluster_chain(self, chain, last_secs):
        """
        chain: list of cluster numbers
        last_secs: number of sectors used in the last cluster
        """
        res = bytearray()
        num_secs = [ self.sect_per_cluster for _ in range(len(chain)) ]
        num_secs[-1] = last_secs
        for cluster, num_sec in zip(chain, num_secs):
            LBA = self.cluster_to_LBA(cluster)
            for ofst in range(num_sec):
                sect_data = self.image.read_sector_LBA(LBA + ofst)['sect_data']
                res.extend(sect_data)
        return res

    def read_file(self, file_name:str):
        file_name, file_name_j, file_type, ascii_flag, random_access_flag, top_cluster, num_sectors = self.get_directory_entry(file_name)
        chain, last_secs = self.trace_FAT_chain(top_cluster)
        file_data = self.read_cluster_chain(chain, last_secs)
        return file_data

    def set_image(self, image:FLOPPY_DISK_D88):
        self.image = image
        id_sect = image.read_sector(0, (0, 0, 3))
        if id_sect['sect_data'][0] != ord('S'):
            print('ERROR: Wrong disk ID. Not a F-BASIC disk.')

