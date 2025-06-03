import json
import os
import shutil
import struct
import subprocess
from HexNavigator import HexNavigator

def get_first_file(path):
    try:
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                return full_path
        return None  # No files found
    except Exception as e:
        print(f"Error: {e}")
        return None

def loadPtrs(settings, filename):
    # Load JSON file
    with open('songs.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract data vault
    binLoc = os.path.join(settings["game"], 'SOUND', 'BURNOUTGLOBALDATA.BIN')
    tempLoc = os.path.join('temp', 'globaldata')
    subprocess.run([settings["yap"], 'e', binLoc, tempLoc])
    # Create a navigator
    vaultLoc = os.path.join(tempLoc, 'AttribSysVault')

    navigator = HexNavigator(get_first_file(vaultLoc))

    # Find the pointer to strings
    navigator.seek(0x08)
    offset = navigator.read_uint32('<')
    print(offset)
    bin_size = navigator.read_uint32('<')
    print(bin_size)

    # now find the ptr base
    navigator.find("NrtP")
    ptr_base = navigator.loc()
    out = {}
    for s in data.keys():
        out[s] = {}
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
            out[song]["strings"] = {"title":song, "stream":stream, "artist":artist, "album":album}
            out[song]["locs"] = {"title":song_pos, "stream":stream_pos, "artist":artist_pos, "album":album_pos}
            # get pointers
            temp_pos = navigator.loc()
            for pos in [song_pos, stream_pos, artist_pos, album_pos]:
                if pos != 0:
                    prefix = bytes.fromhex('03 00 01 00')
                    pos_bytes = struct.pack('<I', pos - offset)
                    search_string = prefix + pos_bytes
                    locs = navigator.find_all(search_string, start=0, hex=True)
                    if pos == song_pos:
                        song_ptr = [loc + 4 for loc in locs]
                    if pos == stream_pos:
                        stream_ptr = [loc + 4 for loc in locs]
                    if pos == artist_pos:
                        artist_ptr = [loc + 4 for loc in locs]
                    if pos == album_pos:
                        album_ptr = [loc + 4 for loc in locs]
                else:
                    if pos == song_pos:
                        song_ptr = []
                    if pos == stream_pos:
                        stream_ptr = []
                    if pos == artist_pos:
                        artist_ptr = []
                    if pos == album_pos:
                        album_ptr = []
            navigator.seek(temp_pos)
            out[song]["ptrs"] = {"title":song_ptr, "stream":stream_ptr, "artist":artist_ptr, "album":album_ptr}
            game = r"C:\Program Files (x86)\Steam\steamapps\common\Burnout(TM) Paradise The Ultimate Box"
            out[song]["file"] = f"{game}\SOUND\STREAMS\{stream}.SNS"
            # out[song]["source"] = ""

    # Save the modified JSON back to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=4, ensure_ascii=False)

    navigator.close()
    f.close()


def writePtrs(soundtrack, settings):
    with open(soundtrack, 'r', encoding='utf-8') as f:
        st = json.load(f)
    
    with open('ptrs.json', 'r', encoding='utf-8') as f:
        ptrs = json.load(f)

    with open('songs.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # get some paths
    binLoc = os.path.join(settings["game"], 'SOUND', 'BURNOUTGLOBALDATA.BIN')
    tempLoc = os.path.join('temp', 'globaldata')

    # create navigator
    vaultLoc = os.path.join(tempLoc, 'AttribSysVault')
    navigator = HexNavigator(get_first_file(vaultLoc))

    # Find the pointer to strings
    navigator.seek(0x08)
    offset = navigator.read_uint32('<')
    to_convert = []

    # put a null character to give us space
    navigator.seek_end()
    navigator.write_bytes(b'\x00')

    for s in st.keys():
        # get defaults
        default = data[s]["defaults"]
        # if something differs between default and soundtrack, write it to the end of the vault and point the pointer to it
        for k in default.keys():
            if (st[s]["strings"][k] != default[k]):
                navigator.seek_end()
                loc = navigator.loc()
                print("got eof " + str(loc))
                navigator.write_cstring(st[s]["strings"][k])
                navigator.seek(ptrs[s]["ptrs"][k])
                navigator.write_bytes((loc - offset).to_bytes(4, 'little'))
        # add to conversion queue
        to_convert.append([st[s]["file"], st[s]["strings"]["stream"].upper(), s])
    # finally, adjust bin size
    navigator.seek_end()
    loc = navigator.loc()
    navigator.seek(0x0c)
    navigator.write_bytes((loc - offset).to_bytes(4, 'little'))
    # now everything is written, let's pack it up
    navigator.close()

    # first turn the bin into bin.old
    backupLoc = binLoc + '.old'
    shutil.move(binLoc, backupLoc)

    # create at the location of the bin
    subprocess.run([settings["yap"], 'c', tempLoc, binLoc])

    # now that the song strings are written, let's convert the songs and update stream headers
    # start by unpacking streamheaders
    headersLoc = os.path.join(settings["game"], "SOUND", "STREAMS", "STREAMHEADERS.BUNDLE")
    tempLoc = os.path.join("temp", "streamheaders")
    subprocess.run([settings["yap"], 'e', headersLoc, tempLoc])
    for s in to_convert:
        # start by converting the song
        convertSong(s[0], s[1], data, settings)
        # get the .snr file, then write those contents at 0x10 of the corresponding data file
        snr_path = os.path.join("temp", s[1] + ".SNR")
        dat_path = os.path.join(tempLoc, "GenericRwacWaveContent", data[s[2]]["id"].upper() + ".dat")
        # get snr data
        with open(snr_path, 'rb') as f:
            snr_data = f.read()
        dat_navigator = HexNavigator(dat_path)
        dat_navigator.seek(0x10)
        # write new length
        dat_navigator.write_bytes(snr_data)
        dat_navigator.close()
        # now slap the file into STREAMS
        sns_path = os.path.join("temp", s[1] + ".sns")
        shutil.copy(sns_path, os.path.join(settings["game"], "SOUND", "STREAMS", s[1].upper() + ".SNS"))
    # repack streamheaders
    subprocess.run([settings["yap"], 'c', tempLoc, headersLoc])



def convertSong(file, stream, data, settings):
    print(file)
    print(stream)
    temp_path = os.path.join("temp", stream)
    subprocess.run([settings["sx"], '-sndplayer', '-ealayer3_int', '-playlocstream', file, f"-=\"{temp_path}\""])
    

    

# settings = {
#     "game": r"C:\Program Files (x86)\Steam\steamapps\common\Burnout(TM) Paradise The Ultimate Box",
#     "yap": r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\YAP\YAP.exe",
#     "sx": r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\sx.exe"
#     }
# loadPtrs(settings, "ptrs.json")
# writePtrs(r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\valid.soundtrack", settings)