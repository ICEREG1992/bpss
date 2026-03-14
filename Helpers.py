import os
import sys
import re

MAX_PATH_LENGTH = 240
MAX_FILENAME_LENGTH = 120
EXTENDED_PATH_PREFIX = "\\\\?\\"
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9 _.\-()\\/:]+$")
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9 _.\-()]+$")

def resource_path(path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, path)

def validate_path_rules(path, label, extensions=None, enforce_filename_rules=False):
    cleaned = (path or "").strip()
    if not cleaned:
        return None, "Invalid Path", f"{label} path is empty."

    normalized = os.path.normpath(cleaned)
    filename = os.path.basename(normalized)

    if normalized.startswith(EXTENDED_PATH_PREFIX):
        return None, "Unsupported Path Syntax", (
            f"{label} uses extended Windows path syntax (\\\\?\\), which is not supported by sx.\n\n"
            f"Path:\n{normalized}"
        )

    if not SAFE_PATH_RE.fullmatch(normalized):
        return None, "Unsupported Characters", (
            f"{label} path contains unsupported characters.\n"
            "Use only letters, numbers, spaces, dashes, underscores, periods, slashes, and parentheses.\n\n"
            f"Path:\n{normalized}"
        )

    if len(normalized) > MAX_PATH_LENGTH:
        return None, "Path Too Long", (
            f"{label} path is too long ({len(normalized)} characters).\n"
            f"Maximum supported length is {MAX_PATH_LENGTH} characters.\n\n"
            f"Path:\n{normalized}"
        )

    if enforce_filename_rules:
        if len(filename) > MAX_FILENAME_LENGTH:
            return None, "File Name Too Long", (
                f"{label} file name is too long ({len(filename)} characters).\n"
                f"Maximum supported length is {MAX_FILENAME_LENGTH} characters.\n\n"
                f"File name:\n{filename}"
            )

        if not SAFE_FILENAME_RE.fullmatch(filename):
            return None, "Unsupported Characters", (
                f"{label} file name contains unsupported characters.\n"
                "Use only letters, numbers, spaces, dashes, underscores, periods, and parentheses.\n\n"
                f"File name:\n{filename}"
            )

    if extensions:
        expected = tuple(ext.lower() for ext in extensions)
        if not normalized.lower().endswith(expected):
            return None, "Incorrect Format", (
                f"{label} must use one of these extensions: {', '.join(extensions)}."
            )

    return normalized, None, None

def require_path_rules(path, label, extensions=None, enforce_filename_rules=False):
    normalized, _, error_message = validate_path_rules(
        path,
        label,
        extensions=extensions,
        enforce_filename_rules=enforce_filename_rules,
    )
    if error_message:
        raise ValueError(error_message)
    return normalized

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
