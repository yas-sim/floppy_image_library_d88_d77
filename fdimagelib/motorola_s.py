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

    def set_data(self, address:int, data:int) -> None:
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
            sum &= 0xff
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

    def generate_records(self) -> str:
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
        