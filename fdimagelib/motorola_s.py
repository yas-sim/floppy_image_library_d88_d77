import struct

from typing import *

class DATA_BUFFER_FOR_MOTOROLAS:
    def __init__(self) -> None:
        self.buffer = []
        self.top_address = 0
        self.bottom_address = 0
        self.data_per_record = 16       # 32 is more common

    def set_top_address(self, address:int) -> None:
        assert address >= 0 and address <= 0xffff
        self.top_address = address
        self.bottom_address = address

    def append(self, data:int) -> None:
        assert data >= 0 and data <= 0xff
        self.buffer.append(data)
        self.bottom_address = self.top_address + len(self.buffer) -1

    def set_data(self, address:int, data:int, extend=False) -> None:
        if extend:
            if address < self.top_address:                  # Extend the buffer towards low address
                diff = self.top_address - address
                self.buffer = [0] * diff + self.buffer
                self.top_address = address
            elif address >= self.bottom_address:             # Extend the buffer towards high address
                diff = address - self.bottom_address + 1
                self.buffer = self.buffer + [0] * diff
                self.bottom_address = self.bottom_address + diff
        assert address >= self.top_address and address <= self.bottom_address
        self.buffer[address - self.top_address] = data

    def range_check(self, address:int) -> int:
        if address >= self.top_address and address <= self.bottom_address:
            return 1                                                        # address is in the range of data buffer
        elif address == self.bottom_address + 1:
            return 2                                                        # address is bottom_address +1 
        else:
            return 0                                                        # address is out of range

    def generate_records(self, record_type:int) -> str:
        srec = ''
        srec_buf = ''
        addr = self.top_address
        pos = 0
        while pos < len(self.buffer):
            num_data_left = len(self.buffer) - pos
            if num_data_left >= self.data_per_record:
                num_data = self.data_per_record
            else:
                num_data = num_data_left
            srec = f'S{str(record_type)}{2+num_data+1:02X}{addr+pos:04X}'   # 2==address field, 1=check sum field
            for count in range(num_data):
                data = self.buffer[pos + count]
                srec += f'{data:02X}'
            # Calculate check sum
            sum = 0
            for dt in srec[2:]:                                             # Skip 'S' and record type ('S0', 'S1', ...)
                sum += ord(dt)
            sum = ~sum & 0xff                                               # complement of 1
            srec += f'{sum:02X}\n'
            srec_buf += srec

            srec = ''
            pos += num_data
        return srec_buf


class MOTOROLA_S:
    def __init__(self) -> None:
        self.buffers:DATA_BUFFER_FOR_MOTOROLAS = []
        self.header = None
        self.entry_address = None
    
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
        if len(self.buffers) == 0:
            new_buffer = DATA_BUFFER_FOR_MOTOROLAS()
            new_buffer.set_top_address(address)
            new_buffer.append(data)
            self.buffers.append(new_buffer)
            return
        for buffer in self.buffers:
            range = buffer.range_check(address)
            match range:
                case 0:
                    new_buffer = DATA_BUFFER_FOR_MOTOROLAS()
                    new_buffer.set_top_address(address)
                    new_buffer.append(data)
                    self.buffers.append(new_buffer)
                case 1:
                    buffer.set_data(address, data)
                case 2:
                    buffer.append(data)

    def encode(self) -> str:
        """
        Encode the buffer contents and generates Motorola S-records
        """
        srecords = ''
        if self.header is not None:
            srec = DATA_BUFFER_FOR_MOTOROLAS()
            srec.set_top_address(0)
            [ srec.append(dt) for dt in self.header ]
            srec_buf = srec.generate_records(0)
            srecords += srec_buf
            del srec

        for srec in self.buffers:
            srec_buf = srec.generate_records(1)
            srecords += srec_buf

        if self.entry_address is not None:
            srec = DATA_BUFFER_FOR_MOTOROLAS()
            srec.set_top_address(self.entry_address)
            srec_buf = srec.generate_records(9)
            srecords += srec_buf

        return srecords
    
    def decode(self, srecords:str, check_check_sum:bool=True) -> Tuple[int, bytes]:
        """
        Decode a Motorola-S text data.
            Return: (entry_address, data, header)
        """
        header = []
        srec = DATA_BUFFER_FOR_MOTOROLAS()
        first_record = True
        entry_address = None
        lines = srecords.splitlines()
        for line in lines:
            type, bytes, address, payload, sum = self.decode_record(line, check_check_sum)
            match type:
                case 0:     # Header
                    header = payload
                case 1:     # Data
                    if first_record:
                        first_record = False
                        srec.set_top_address(address)
                    for pos, dt in enumerate(payload):
                        srec.set_data(address+pos, dt, extend=True)
                case 9:     # End
                    entry_address = address
                case _:
                    raise ValueError(f'Unsupported record type ({type})')
        data = srec.buffer
        top_address = srec.top_address
        return (top_address, data, entry_address)


    def decode_record(self, srec_str:str, check_check_sum:bool=True) -> Tuple[int, int, int, bytes, int]:
        """
        Decode single Motorola-S record.
            Return: (type, bytes, address, payload, sum)
        """
        if srec_str[0] != 'S':
            raise ValueError(f'Not a Motorola-S record ({srec_str})')
        type = int(srec_str[1])
        if type not in (0, 1, 9):
            return ValueError(f'Unsupported record type ({type})')
        srec_str = srec_str.replace('\n', '')
        srec_str = srec_str.replace('\r', '')
        num_bytes = int('0x'+srec_str[2:2+2] ,16)
        address = int('0x'+srec_str[4:4+4], 16)
        payload = bytes([ int('0x'+(srec_str[8+pos*2 : 10+pos*2]), 16) for pos in range(num_bytes-3) ])
        # SUM = num_bytes + address + payload
        true_sum = int('0x'+srec_str[-2:], 16)
        sum = ((num_bytes>>8) & 0xff) + (num_bytes & 0xff) + ((address>>8) & 0xff) + (address & 0xff)
        for dt in payload:
            sum += dt
        sum = ~sum & 0xff
        if check_check_sum and sum != true_sum:
            raise ValueError(f'Check sum mismatch (True={true_sum:02x}:{sum:02x})')
        return (type, num_bytes, address, payload, sum)
