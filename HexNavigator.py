import struct
import json

class HexNavigator:
    def __init__(self, filepath):
        self.file = open(filepath, 'rb')

    def seek(self, offset):
        # print(f"Seeking to offset 0x{offset:X}")
        self.file.seek(offset)

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

# Load JSON file
with open('songs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Create a navigator
navigator = HexNavigator(r"C:\temp\bundle\AttribSysVault\7657D9BF.dat")

# Find the pointer to strings
navigator.seek(0x08)
offset = navigator.read_uint32('<')
print(offset)
bin_size = navigator.read_uint32('<')
print(bin_size)

# now find the ptr base
navigator.find("NrtP")
ptr_base = navigator.loc()

# start consuming tokens
navigator.seek(offset)
while (navigator.loc() < offset + bin_size):
    song_pos = navigator.loc()
    song = navigator.read_cstring()
    if song in data:
        match data[song]["type"]:
            case 0: # regular soundtrack
                match data[song]["lock"]:
                    case 0: # no lock
                        stream_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist_pos = navigator.loc()
                        artist = navigator.read_cstring()
                        album_pos = navigator.loc()
                        album = navigator.read_cstring()
                    case 1: # no album (FRICTION)
                        stream_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist_pos = navigator.loc()
                        artist = navigator.read_cstring()
                        album_pos = 0
                        album = ""
                    case 3: # artist/album sync
                        stream_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist_pos = navigator.loc()
                        album_pos = navigator.loc()
                        artist = navigator.read_cstring()
                        album = artist
                    case 6: # stream/artist sync
                        stream_pos = navigator.loc()
                        artist_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist = stream
                        album_pos = navigator.loc()
                        album = navigator.read_cstring()
                    case 7: # stream/artist/album sync
                        stream_pos = navigator.loc()
                        artist_pos = navigator.loc()
                        album_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist = stream
                        album = stream
                    case 9: # song/album sync
                        stream_pos = navigator.loc()
                        stream = navigator.read_cstring()
                        artist_pos = navigator.loc()
                        artist = navigator.read_cstring()
                        album_pos = song_pos
                        album = song
            case 1: # burnout soundtrack
                # get stream name
                stream_pos = navigator.loc()
                stream = navigator.read_cstring()
                # save pos, check for more
                temp_pos = navigator.loc()
                artist = navigator.read_cstring()
                if artist == data[song]["defaults"]["artist"]:
                    artist_pos = temp_pos
                else:
                    artist = ""
                    artist_pos = 0
                    navigator.seek(temp_pos)
                temp_pos = navigator.loc()
                album = navigator.read_cstring()
                if album == data[song]["defaults"]["album"]:
                    album_pos = temp_pos
                else:
                    album = ""
                    album_pos = 0
                    navigator.seek(temp_pos)
            case 2: # classical soundtrack
                stream_pos = navigator.loc()
                stream = navigator.read_cstring()
                # save pos, check for artist
                temp_pos = navigator.loc()
                artist = navigator.read_cstring()
                if artist == data[song]["defaults"]["artist"]:
                    artist_pos = temp_pos
                else:
                    artist = ""
                    artist_pos = 0
                    navigator.seek(temp_pos)
                album_pos = 0
                album = ""
        data[song]["strings"] = {"title":song, "stream":stream, "artist":artist, "album":album}
        data[song]["locs"] = {"title":song_pos, "stream":stream_pos, "artist":artist_pos, "album":album_pos}
        # get pointers
        temp_pos = navigator.loc()
        for pos in [song_pos, stream_pos, artist_pos, album_pos]:
            if pos != 0:
                prefix = bytes.fromhex('03 00 01 00')
                pos_bytes = struct.pack('<I', pos - offset)
                search_string = prefix + pos_bytes
                print(navigator.find(search_string, hex=True))
                if pos == song_pos:
                    song_ptr = navigator.loc() + 4
                if pos == stream_pos:
                    stream_ptr = navigator.loc() + 4
                if pos == artist_pos:
                    artist_ptr = navigator.loc() + 4
                if pos == album_pos:
                    album_ptr = navigator.loc() + 4
            else:
                if pos == song_pos:
                    song_ptr = 0
                if pos == stream_pos:
                    stream_ptr = 0
                if pos == artist_pos:
                    artist_ptr = 0
                if pos == album_pos:
                    album_ptr = 0
        navigator.seek(temp_pos)
        data[song]["ptrs"] = {"title":song_ptr, "stream":stream_ptr, "artist":artist_ptr, "album":album_ptr}
        game = r"C:\Program Files (x86)\Steam\steamapps\common\Burnout(TM) Paradise The Ultimate Box"
        data[song]["file"] = f"{game}\SOUND\STREAMS\{stream}.SNS"
        data[song]["source"] = ""

# Save the modified JSON back to file
with open('locs.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

navigator.close()
f.close()