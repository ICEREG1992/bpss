import json
import os
import shutil
import struct
import subprocess
import zipfile
from HexNavigator import HexNavigator
from Helpers import resource_path
from PyQt5.QtCore import QThread
import soundfile as sf

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

def load_pointers(settings, filename, set_progress=None):
    if set_progress: set_progress(0, "Loading data from files...")
    
    # Load JSON file
    with open(resource_path("defaults.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)

    if set_progress: set_progress(5, "Extracting string data...")

    # Extract data vault
    if "game" in settings.keys() and os.path.isdir(settings["game"]):
        binLoc = os.path.join(settings["game"], 'SOUND', 'BURNOUTGLOBALDATA.BIN')
        tempLoc = os.path.join('temp', 'globaldata')
        subprocess.run([settings["yap"], 'e', binLoc, tempLoc], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        print("failing out")
        if set_progress: set_progress(100, "Failed to find Burnout Paradise installation!")
        return

    if set_progress: set_progress(10, "Navigating string data...")

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

    if set_progress: set_progress(20, "Finding strings...")
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
                            # check for the almighty empty string
                            temp_pos = navigator.loc()
                            album = navigator.read_cstring()
                            if album == data[song]["defaults"]["album"]:
                                album_pos = temp_pos
                            else:
                                album = ""
                                album_pos = 0
                                navigator.seek(temp_pos)
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
                        artist = data[song]["defaults"]["artist"]
                        artist_pos = 0
                        navigator.seek(temp_pos)
                    temp_pos = navigator.loc()
                    album = navigator.read_cstring()
                    if album == data[song]["defaults"]["album"]:
                        album_pos = temp_pos
                    else:
                        album = data[song]["defaults"]["album"]
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
                        artist = data[song]["defaults"]["artist"]
                        artist_pos = 0
                        navigator.seek(temp_pos)
                    # check for the almighty empty string
                    temp_pos = navigator.loc()
                    album = navigator.read_cstring()
                    if album == data[song]["defaults"]["album"]:
                        album_pos = temp_pos
                    else:
                        album = data[song]["defaults"]["album"]
                        album_pos = 0
                        navigator.seek(temp_pos)
            out[song]["strings"] = {"title":song, "stream":stream, "artist":artist, "album":album}
            out[song]["locs"] = {"title":song_pos, "stream":stream_pos, "artist":artist_pos, "album":album_pos}
            # get pointers

            if set_progress: set_progress(60, "Finding pointers...")

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
            # out[song]["source"] = ""

    if set_progress: set_progress(90, "Writing pointer data...")

    # Save the modified JSON back to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=4, ensure_ascii=False)

    navigator.close()
    if set_progress: set_progress(100, "Done!")


def write_pointers(settings, soundtrack, pointers, set_progress=None):
    if not soundtrack:
        if set_progress: set_progress(100, "Nothing to apply.")
        return
    if set_progress: set_progress(0, "Loading data from files...")

    # Establish thread in case we want to cancel later
    thread = QThread.currentThread()
    
    with open(soundtrack, 'r', encoding='utf-8') as f:
        st = json.load(f)
    
    with open(pointers, 'r', encoding='utf-8') as f:
        ptrs = json.load(f)

    with open(resource_path("defaults.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)

    if set_progress: set_progress(3, "Locating string data...")

    # get some paths
    binLoc = os.path.join(settings["game"], 'SOUND', 'BURNOUTGLOBALDATA.BIN')
    tempLoc = os.path.join('temp', 'globaldata')

    # create navigator
    vaultLoc = os.path.join(tempLoc, 'AttribSysVault')
    if not os.path.isdir(vaultLoc):
        # temp directory got deleted
        subprocess.run([settings["yap"], 'e', binLoc, tempLoc], creationflags=subprocess.CREATE_NO_WINDOW)
    navigator = HexNavigator(get_first_file(vaultLoc))

    print(f"##########  {os.getcwd()}")

    if set_progress: set_progress(8, "Beginning data write...")

    # Find the pointer to strings
    navigator.seek(0x08)
    offset = navigator.read_uint32('<')
    to_convert = []

    # put a null character to give us space
    navigator.seek_end()
    navigator.write_bytes(b'\x00')

    steps = len(st.keys()) or 1
    step = 20 / steps
    count = 0
    written_pointers = []
    for s in st.keys():
        print(f"writing data for {s}")
        if set_progress: set_progress(int((step * count) + 10), f"Writing strings for \"{st[s]['strings']['title']}\"...")
        # get defaults
        default = data[s]["defaults"]
        # if something differs between default and soundtrack, write it to the end of the vault and point the pointer to it
        for k in default.keys():
            if (st[s]["strings"][k] != default[k]):
                navigator.seek_end()
                loc = navigator.loc()
                # print("got eof " + str(loc))
                navigator.write_cstring(st[s]["strings"][k])
                if ptrs[s]:
                    # if overrides specified, use that
                    if ptrs[s].get("overrides") and ptrs[s]["overrides"].get(k):
                        navigator.seek(ptrs[s]["overrides"][k])
                        navigator.write_bytes((loc - offset).to_bytes(4, 'little'))
                        written_pointers.append(x)
                    else:
                        for x in ptrs[s]["ptrs"][k]:
                            if x not in written_pointers:
                                navigator.seek(x)
                                navigator.write_bytes((loc - offset).to_bytes(4, 'little'))
                                written_pointers.append(x)
        # add to conversion queue
        if st[s].get("zip", None):
            to_convert.append([st[s]["zip"], st[s]["strings"]["stream"].upper(), s])
        elif st[s]["source"]:
            to_convert.append([st[s]["source"], st[s]["strings"]["stream"].upper(), s])
        count += 1

    if set_progress: set_progress(30, "Adjusting bin size...")

    # finally, adjust bin size
    navigator.seek_end()
    loc = navigator.loc()
    navigator.seek(0x0c)
    navigator.write_bytes((loc - offset).to_bytes(4, 'little'))
    # now everything is written, let's pack it up
    navigator.close()

    if set_progress: set_progress(35, "Packing bin...")

    # first turn the bin into bin.old if one doesn't exist already
    backupLoc = binLoc + '.old'
    if not os.path.exists(backupLoc):
        shutil.move(binLoc, backupLoc)

    # create at the location of the bin
    subprocess.run([settings["yap"], 'c', tempLoc, binLoc], creationflags=subprocess.CREATE_NO_WINDOW)

    if set_progress: set_progress(40, "Unpacking stream headers...")

    # now that the song strings are written, let's convert the songs and update stream headers
    # start by unpacking streamheaders
    headersLoc = os.path.join(settings["game"], "SOUND", "STREAMS", "STREAMHEADERS.BUNDLE")
    tempLoc = os.path.join("temp", "streamheaders")
    subprocess.run([settings["yap"], 'e', headersLoc, tempLoc], creationflags=subprocess.CREATE_NO_WINDOW)

    steps = len(to_convert) or 1
    step = (50 / steps)
    count = 0
    for s in to_convert:
        if thread.isInterruptionRequested():
            if set_progress: set_progress(100, "Apply action canceled. Changes may be partially applied.")
            return
        if set_progress: set_progress(int((step * count) + 45), f"Converting \"{st[s[2]]['strings']['title']}\"...")
        # start by converting the song
        convertSong(s[0], s[1], settings)
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
        
        # write original .sns to .old
        temp_sns_path = os.path.join("temp", s[1] + ".sns")
        sns_path = os.path.join(settings["game"], "SOUND", "STREAMS", s[1].upper() + ".SNS")
        backupSns = sns_path + ".old"
        if not os.path.exists(backupSns):
            shutil.move(sns_path, backupSns)
        # now slap the file into STREAMS
        shutil.copy(temp_sns_path, sns_path)
        
        count += 1
    # write original streamheaders to .old
    # repack streamheaders
    if set_progress: set_progress(95, "Packing stream headers...")

    backupHeaders = headersLoc + ".old"
    if not os.path.exists(backupHeaders):
        shutil.move(headersLoc, backupHeaders)
    subprocess.run([settings["yap"], 'c', tempLoc, headersLoc], creationflags=subprocess.CREATE_NO_WINDOW)

    # save edits to st too
    with open(soundtrack, 'w', encoding='utf-8') as f:
        json.dump(st, f, indent=4, ensure_ascii=False)

    if set_progress: set_progress(100, "Done!")

def reset_files(settings, set_progress=None):
    changed = False
    if set_progress: set_progress(0, "Restoring strings...")

    # Establish thread in case we want to cancel later
    thread = QThread.currentThread()

    # search for restore .old files at locations we'd expect them
    if "game" in settings.keys() and os.path.isdir(settings["game"]):
        binLoc = os.path.join(settings["game"], 'SOUND', 'BURNOUTGLOBALDATA.BIN')
    else:
        if set_progress: set_progress(100, "Failed to find Burnout Paradise installation!")
        return

    backupLoc = binLoc + '.old'
    if os.path.exists(backupLoc):
        print(f"Restoring {binLoc}")
        shutil.move(backupLoc, binLoc)
        changed = True

    if set_progress: set_progress(10, "Restoring stream headers...")

    headersLoc = os.path.join(settings["game"], "SOUND", "STREAMS", "STREAMHEADERS.BUNDLE")
    backupHeaders = headersLoc + ".old"
    if os.path.exists(backupHeaders):
        print(f"Restoring {headersLoc}")
        shutil.move(backupHeaders, headersLoc)
        changed = True

    if set_progress: set_progress(20, "Scanning audio files...")

    # look for files
    snsLoc = os.path.join(settings["game"], "SOUND", "STREAMS")
    file_queue = []
    for dirpath, _, filenames in os.walk(snsLoc):
        for filename in filenames:
            if filename.endswith('.old'):
                if thread.isInterruptionRequested():
                    if set_progress: set_progress(100, "Reset action canceled. Changes may be partially applied.")
                    return
                original_name = filename[:-4]
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, original_name)
                if os.path.exists(new_path):
                    file_queue.append((old_path, new_path))

    step = 75 / (len(file_queue) or 1)
    count = 0
    for old_path, new_path in file_queue:
        if set_progress: set_progress(int((step * count) + 25), f"Restoring \"{new_path}\"...")
        print(f"Restoring {new_path}")
        shutil.move(old_path, new_path)
        changed = True
        count += 1

    end_message = "Done!" if changed else "Nothing to revert."
    if set_progress: set_progress(100, end_message)


def convertSong(file, stream, settings):
    print(file)
    print(stream)
    temp_path = os.path.join("temp", stream)
    subprocess.run([settings["audio"], '-sndplayer', '-ealayer3_int', '-vbr100', '-playlocstream', f"\"file\"", f"-=\"{temp_path}\""], creationflags=subprocess.CREATE_NO_WINDOW)
    

def export_files(settings, filename, export_path, set_progress=None):
    if set_progress: set_progress(0, "Exporting soundtrack...")
    with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(filename, os.path.basename(filename))

        if set_progress: set_progress(10, "Loading paths...")

        with open(filename, 'r', encoding='utf-8') as f:
            st = json.load(f)

        step = 90 / (len(st.keys()) or 1)
        count = 0
        for s in st.keys():
            if set_progress: set_progress(int((step * count) + 10), f"Exporting \"{st[s]['strings']['title']}\"...")
            if st[s]["source"]:
                source_path = st[s]["source"]
                z.write(source_path, os.path.basename(source_path))
            count += 1

        if set_progress: set_progress(100, "Done!")

# settings = {
#     "game": r"C:\Program Files (x86)\Steam\steamapps\common\Burnout(TM) Paradise The Ultimate Box",
#     "yap": r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\YAP\YAP.exe",
#     "audio": r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\sx.exe"
#     }
# loadPtrs(settings, "ptrs.json")
# writePtrs(r"C:\Users\willw\OneDrive\Documents\GitHub\bpss\valid.soundtrack", settings)