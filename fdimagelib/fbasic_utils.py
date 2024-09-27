import struct
from enum import Enum

from fdimagelib.fbasic_ir_table import ir_table, ir_table_ff
from fdimagelib.ascii_j import *

def decode_float(data:bytearray):
    exponent = data[0]
    mantissa_MSB = 1 if exponent & 0x80 else 0
    exponent = exponent & 0x7f
    if exponent & 0x40:
        exponent = (exponent ^ 0x7f) - 1        # complement of 2
    tmpbuf = data.copy()
    tmpbuf[0] = 0
    tmpbuf[1] |= 0x80 if mantissa_MSB == 1 else 0x00
    mantissa = struct.unpack_from('>I', tmpbuf, 0)[0]
    mantissa /= 0x1000000
    value = mantissa * (2**exponent)
    return value

def decode_double(data:bytearray):
    exponent = data[0]
    mantissa_MSB = 1 if exponent & 0x80 else 0
    exponent = exponent & 0x7f
    if exponent & 0x40:
        exponent = (exponent ^ 0x7f) - 1        # complement of 2
    tmpbuf = data.copy()
    tmpbuf[0] = 0
    tmpbuf[1] |= 0x80 if mantissa_MSB == 1 else 0x00
    mantissa = struct.unpack_from('>Q', tmpbuf, 0)[0]
    mantissa /= 0x100000000000000
    value = mantissa * (2**exponent)
    return value


class Decode_State(Enum):
    skip_link = 0
    line_num = 1
    ir_dec = 2
    ir_dec_ff = 3
    string = 4
    remark = 5
    literal = 6


class Token_Type(Enum):
    keyword = 0
    literal = 1
    new_line = 2
    string_literal = 3
    remark = 4
    line_number = 5
    EOL = 6
    plain_chars = 7
    others = 8


class String_Buffer:
    def __init__(self):
        self.data = ''
        self.deferred_string = ''
        self.previous_type = Token_Type.others

    def set_deferred_string(self, deferred_string):
        self.deferred_string = deferred_string

    def clear_deferred_string(self):
        self.deferred_string = ''
    
    def add_string(self, token_string, token_type:Token_Type):
        token_string = asciij_string_to_utf8(token_string)
        if token_string == ':':
            if self.previous_type == Token_Type.line_number:      # Ignore ':' right after the line number
                return
            elif self.deferred_string == ':':
                self.deferred_string = ''
            else:
                self.deferred_string = ':'                        # Defer adding ':' until next keyword is determined, and it's not either one of "'" or "ELSE"
                return
        if token_string in [ '\'', 'REM', 'ELSE']:
            self.deferred_string = ''

        self.data += self.deferred_string
        if token_type == Token_Type.keyword or token_type == Token_Type.plain_chars:
            if self.previous_type == Token_Type.line_number:
                self.data += ' '
        self.data += token_string

        self.deferred_string = ''
        self.previous_type = token_type

    def clear_buffer(self):
        self.__init__()

    def finalize(self):
        self.data += self.deferred_string
        self.deferred_string = ''
        return self.data


def F_BASIC_IR_decode(ir_data):
    ir_codes = list(ir_table.keys())
    ir_min = min(ir_codes)
    ir_max = max(ir_codes)
    ir_codes = list(ir_table_ff.keys())
    ir_min_ff = min(ir_codes)
    ir_max_ff = max(ir_codes)
    res = String_Buffer()
    # Link pointer (XX,XX), Line Number (XX, XX), IR/Literal, Line separator (0x00)
    # Line number: 0xfe 0xf2 0xXX 0xXX
    # Line separator: 0x00
    state = Decode_State.skip_link
    count = 0
    line_num = 0
    literal_type = 0
    literal_val = 0
    decode_buf = bytearray()
    #special_chars = ' =+-*/\^()%#$!&@,.\';:?<>"_'
    special_chars = ' =+-*/\^()%#$!&@,.;:?<>"_'
    for ir in ir_data:
        match state:
            case Decode_State.skip_link:
                count += 1
                if count < 2:
                    continue
                count = 0
                decode_buf = bytearray()
                state = Decode_State.line_num
            case Decode_State.line_num:
                count += 1
                decode_buf.extend([ir])
                if count < 2:
                    continue
                line_num = struct.unpack_from('>H', decode_buf, 0)[0]
                count = 0
                res.add_string(str(line_num), Token_Type.line_number)
                state = Decode_State.ir_dec
            case Decode_State.ir_dec:               # BASIC keyword
                if ir == 0x00:                      # Line separator
                    res.add_string('\n', Token_Type.EOL)
                    count = 0
                    state = Decode_State.skip_link
                    continue
                if ir == 0xfe:                      # Constant/Literal value
                    count = 1
                    decode_buf = bytearray([ir])
                    state = Decode_State.literal
                    continue
                if ir == 0xff:
                    state = Decode_State.ir_dec_ff
                    continue
                if ir >= ir_min and ir <= ir_max:
                    keyword = ir_table[ir]
                    res.add_string(keyword, Token_Type.keyword)
                    if keyword == '\'' or keyword == 'REM':
                        state = Decode_State.remark
                    continue
                res.add_string(chr(ir), Token_Type.plain_chars)
                if ir == ord('"'):
                    state = Decode_State.string
            case Decode_State.ir_dec_ff:                        # BASIC keyword with $FF prefix
                if ir >= ir_min_ff and ir <= ir_max_ff:
                    keyword = ir_table_ff[ir]
                    res.add_string(keyword, Token_Type.keyword)
                state = Decode_State.ir_dec
            case Decode_State.literal:
                decode_buf.extend([ir])
                count += 1
                if count == 2:
                    literal_type = ir   # keep the literal type ID
                    continue
                match literal_type:
                    case 0x01:      # 1 byte, signed integer
                        literal_val = int(ir)
                        literal_str = str(literal_val)
                    case 0x02:      # 2 byte, signed integer
                        if count < 2+2:
                            continue
                        literal_val = struct.unpack_from('>H', decode_buf, 2)[0]
                        literal_str = str(literal_val)
                    case 0x04:      # 4 byte, sigle precision floating point [EXP]+[3MAN]
                        if count < 2+4:
                            continue
                        literal_val = decode_float(decode_buf[2:])
                        if int(literal_val) == literal_val:     # no fractional digits
                            literal_str = str(int(literal_val)) + '!'
                        else:
                            literal_str = str(literal_val)
                    case 0x08:      # 8 byte, double precision floating point [EXP]+[7MAN]
                        if count < 2+8:
                            continue
                        literal_val = decode_double(decode_buf[2:])
                        if int(literal_val) == literal_val:     # no fractional digits
                            literal_str = str(int(literal_val)) + '#'
                        else:
                            literal_str = str(literal_val)
                    case 0xf2:      # 2 byte, unsigned integer, dedicatd for line number
                        if count < 2+2:
                            continue
                        literal_val = struct.unpack_from('>H', decode_buf, 2)[0]
                        literal_str = str(literal_val)
                res.add_string(literal_str, Token_Type.literal)
                state = Decode_State.ir_dec
            case Decode_State.string:
                res.add_string(chr(ir), Token_Type.string_literal)
                if ir == ord('"'):
                    state = Decode_State.ir_dec
                if ir == 0x00:
                    res.add_string('\n', Token_Type.EOL)
                    count = 0
                    state = Decode_State.skip_link
                    continue
            case Decode_State.remark:
                if ir == 0x00:                      # Line separator
                    res.add_string('\n', Token_Type.EOL)
                    count = 0
                    state = Decode_State.skip_link
                    continue
                res.add_string(chr(ir), Token_Type.remark)
    return res.finalize()
