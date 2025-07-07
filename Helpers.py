import os
import sys

def resource_path(path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, path)

def col_to_key(col):
    match col:
        case 0:
            return "index"
        case 1:
            return "title"
        case 2:
            return "album"
        case 3:
            return "artist"
        case 4:
            return "stream"
        case 5:
            return "source"