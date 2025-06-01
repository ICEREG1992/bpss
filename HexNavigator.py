import struct
import json

class HexNavigator:
    def __init__(self, filepath):
        self.file = open(filepath, 'r+b')

    def seek(self, offset):
        # print(f"Seeking to offset 0x{offset:X}")
        self.file.seek(offset)

    def seek_end(self):
        self.file.seek(0, 2)  # 0 bytes from the end (whence=2)

    def read_uint32(self, endian='<'):
        data = self.file.read(4)
        fmt = endian + 'I'
        value = struct.unpack(fmt, data)[0]
        # print(f"Read uint32: {value} (0x{value:X})")
        return value

    def read_bytes(self, size):
        data = self.file.read(size)
        # print(f"Read bytes: {data.hex()}")
        return data
    
    def write_bytes(self, data: bytes):
        """Writes raw bytes at the current file position."""
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("write_bytes expects a bytes-like object")
        self.file.write(data)

    def read_cstring(self, encoding='ascii'):
        chars = []
        while True:
            byte = self.file.read(1)
            if byte == b'':
                print("Reached EOF while reading C-string")
                break
            if byte == b'\x00':
                break
            chars.append(byte)
        result = b''.join(chars).decode(encoding, errors='replace')
        # print(f"Read C-string: {result}")
        return result
    
    def write_cstring(self, s: str, encoding='ascii'):
        """Writes a null-terminated string at the current file position."""
        self.write_bytes(s.encode(encoding) + b'\x00')
        
    def find(self, pattern, hex=False, encoding='ascii'):
        """Finds the first occurrence of pattern (hex bytes or ascii string) and seeks there."""
        if hex:
            if isinstance(pattern, bytes):
                needle = pattern  # Already bytes, use as is
            else:
                needle = bytes.fromhex(pattern)
        else:
            needle = pattern.encode(encoding)

        print(f"Searching for pattern: {needle.hex()}")

        self.file.seek(0)
        chunk_size = 4096
        overlap = len(needle) - 1

        pos = 0
        buffer = b''

        while True:
            data = self.file.read(chunk_size)
            if not data:
                break  # EOF

            buffer = buffer[-overlap:] + data
            index = buffer.find(needle)
            if index != -1:
                found_offset = pos + index - overlap
                print(f"Found at offset 0x{found_offset:X}")
                self.seek(found_offset)
                return found_offset

            pos += len(data)

        print("Pattern not found.")
        return -1

    def find_all(self, pattern, hex=False, encoding='ascii'):
        """Finds all occurrences of pattern and returns a list of offsets."""
        if hex:
            if isinstance(pattern, bytes):
                needle = pattern  # Already bytes, use as is
            else:
                needle = bytes.fromhex(pattern)
        else:
            needle = pattern.encode(encoding)

        print(f"Searching for all instances of pattern: {needle.hex()}")

        self.file.seek(0)
        chunk_size = 4096
        overlap = len(needle) - 1

        pos = 0
        buffer = b''
        offsets = []

        while True:
            data = self.file.read(chunk_size)
            if not data:
                break  # EOF

            buffer = buffer[-overlap:] + data

            search_start = 0
            while True:
                index = buffer.find(needle, search_start)
                if index == -1:
                    break

                found_offset = pos + index - overlap
                print(f"Found at offset 0x{found_offset:X}")
                offsets.append(found_offset)

                search_start = index + 1  # keep searching after this match

            pos += len(data)

        if not offsets:
            print("Pattern not found.")

        return offsets

    def loc(self):
        """Returns the current file position (offset)."""
        pos = self.file.tell()
        # print(f"Current position: 0x{pos:X}")
        return pos
    
    def close(self):
        self.file.close()