import struct

from typing import *

class MOTOROLA_S:
    def __init__(self) -> None:
        self.init_data_buffer()
        self.header = None
        self.entry_address = None
        self.record_size = 16        # Data length of one S-record. 32 is most popular
    
    def init_data_buffer(self):
        self.buffer = bytearray()
        self.buffer_top_address = 0xffffffff
        self.buffer_bottom_address = 0

    def set_header(self, data:any) -> int:
        header = []
        if type(data) == str:
            header = list(data.encode())
        elif type(data) in (bytes, bytearray, list, tuple):
            header = list(data)
        else:
            assert False
        self.header = header

    def set_entry_address(self, address:int) -> None:
        assert address >= 0 and address <= 0xffff
        self.entry_address = address

    def add_data(self, address, data) -> None:
        if len(self.buffer) <= address:
            num_extend = address - len(self.buffer) + 1
            self.buffer.extend(bytes(num_extend))
        self.buffer[address] = data
        if self.buffer_bottom_address < address:
            self.buffer_bottom_address = address
        if self.buffer_top_address > address:
            self.buffer_top_address = address



    def generate_srecord(self, record_type:int, address:int, payload:bytes):
        """
        Generate single line of Motorola S-record
        """
        assert record_type >= 0 and record_type <= 9
        address_bytes = [ 2, 2, 3, 4, 0, 2, 3, 4, 3, 2 ][record_type]
        srecord  = f'S{record_type:d}'
        num_bytes = address_bytes + len(payload) + 1    # 1 == check-sum
        srecord += f'{num_bytes:02X}'
        srecord += f'{address:08X}'[-2 * address_bytes:]
        for data in payload:
            srecord += f'{data:02X}'
        sum = 0
        for pos in range(2, len(srecord), 2):   # -2 for 'S' on the top of the record and record type
            hex_str = srecord[pos : pos + 2]
            sum += int(hex_str, 16)
        sum = ~sum & 0xff
        srecord += f'{sum:02X}\n'
        return srecord

    def decode_srecord(self, record:str, enable_check_sum:bool=True) -> Tuple[bool, int, int, bytes]:
        """
        Decode single line of Motorola S-record
            Return: 
                match_sum:bool
                record_type:int
                address:int
                payload:bytes
        """
        record = record.rstrip('\n')
        payload = bytearray()
        address = -1
        record_type = -1
        error_response = (False, -1, -1, bytes())
        assert len(record) >= 5
        if record[0] != 'S':
            return error_response
        record_type = record[1]
        assert record_type.isdecimal()
        record_type = int(record_type)
        num_bytes = int(record[2 : 2 + 2], 16)
        sum = num_bytes
        
        address_bytes = [ 2, 2, 3, 4, 0, 2, 3, 4, 3, 2 ][record_type]
        num_data = num_bytes - address_bytes - 1
        address_offset = 1 + 1 + 1 * 2
        data_offset = address_offset + address_bytes * 2
        csum_offset = data_offset + num_data * 2
        total_record_len = csum_offset + 2

        assert len(record) >= total_record_len
        #assert len(record) == total_record_len        # Strict check

        address = int(record[4 : 4 + address_bytes * 2], 16)
        for n in range(address_bytes):
            sum += (address >> (n * 8)) & 0xff

        for pos in range(num_data):
            hex_str = record[data_offset + pos * 2 : data_offset + pos * 2 + 2]
            dt = int(hex_str, 16)
            payload.append(dt)
            sum += dt

        sum = ~sum & 0xff      # complement of 1
        true_sum = int(record[csum_offset : csum_offset + 2], 16)
        if enable_check_sum and sum != true_sum:
            raise ValueError(f'Check sum mismatch (True={true_sum:02x}:{sum:02x})')

        return (sum == true_sum, record_type, address, bytes(payload))



    def encode(self) -> str:
        """
        Encode the buffer contents and generates Motorola S-records
        """
        srecords = ''
        if self.header is not None:
            srec = self.generate_srecord(0, 0, self.header)
            srecords += srec

        for addr in range(self.buffer_top_address, self.buffer_bottom_address+1, self.record_size):
            rec_top = addr
            rec_bottom = addr + self.record_size
            if rec_bottom > self.buffer_bottom_address:
                rec_bottom = self.buffer_bottom_address
            srec = self.generate_srecord(1, addr, self.buffer[rec_top : rec_bottom + 1])
            srecords += srec

        if self.entry_address is not None:
            srec = self.generate_srecord(9, self.entry_address, bytes())
            srecords += srec

        return srecords
    
    def decode(self, srecords:str, check_check_sum:bool=True) -> Tuple[int, bytes]:
        """
        Decode a Motorola-S text data.
            Return: (entry_address, data, header)
        """
        header = []
        self.init_data_buffer()
        entry_address = None
        lines = srecords.splitlines()
        for line in lines:
            sum, record_type, address, payload = self.decode_srecord(line, check_check_sum)
            if record_type == -1:
                continue            # ignore non S-record lines
            if sum == False:
                raise ValueError(f'Check sum error in S-record : {line}')
            match record_type:
                case 0:             # Header
                    header = payload
                case 1 | 2 | 3:     # Data
                    for pos, dt in enumerate(payload):
                        self.add_data(address + pos, dt)                    
                case 7 | 8 | 9:     # End
                    entry_address = address
                case _:
                    raise ValueError(f'Unsupported record type ({type})')
        valid_data = self.buffer[self.buffer_top_address : self.buffer_bottom_address]
        return (self.buffer_top_address, valid_data, entry_address)
