#!/usr/bin/env python
import sys
import os
from fnmatch import fnmatch
import scandir

_OS = None


__all__ = [
    'get_os',
    'path_normalize',
    'path_contains',
    'join_paths',
    'filter_item',
    'get_folder_contents',
]


def get_os():
    """
    Get the os of the current system in a standard format.
    mac, windows, linux
    """
    global _OS
    if _OS:
        return _OS

    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        result = "windows"
    elif (sys.platform == 'cygwin'):
        result = "cygwin"
    elif (sys.platform.lower() == "darwin"):
        result = "mac"
    else:
        result = "linux"

    _OS = result
    return result


def path_normalize(filename, allowBackslash=False, normcase=False, removeDoubleSlashes=True):
    """
    Normalize filename
    Make sure all slashes match the platform
    """
    slash = "/"
    if get_os() == 'windows' and allowBackslash:
        slash = r"\\"
    if "\\" != slash:
        filename = filename.replace("\\", slash)
    if "/" != slash:
        filename = filename.replace("/", slash)
    if normcase:
        filename = filename.lower()
    if removeDoubleSlashes and filename:
        # Skip first slashes as they can be important
        filename = filename[0] + filename[1:].replace('//', '/')
    return filename


def path_contains(root, path, normalize=True, normcase=True):
    """
    Return True if root contains path
    Prevents false positives such as:
        /root
        /root2/project
    """
    root = root[:-1] if root[-1] in ("\\", "/") else root
    if normalize:
        r, p = path_normalize(root, normcase=normcase), path_normalize(path, normcase=normcase)
    elif normcase:
        r, p = root.lower(), path.lower()
    else:
        r, p = root, path
    result = p.startswith(r)
    splice = p[len(r):]
    if result:
        if len(splice) and splice[0] not in ("\\", "/"):
            return False
        return True
    return False


def join_paths(*paths):
    """
    Join paths using forward slashes
    """
    return os.path.join(*paths).replace('\\', '/')


def filter_item(item, include=['*'], exclude=[]):
    """
    Return True if the given item passes the given filters, False if it doesn't

    `key` - can be given an attrgetter or itemgetter to be used on item
    """
    if not any([fnmatch(item, p) for p in include]):
        return False
    if any([fnmatch(item, p) for p in exclude]):
        return False
    return True


def get_folder_contents(path, includeFiles=True, includeDirs=True, **kwargs):
    paths = []
    if os.path.isdir(path):
        for entry in scandir.scandir(path):
            if not includeFiles and entry.is_file():
                continue
            if not includeDirs and entry.is_dir():
                continue
            if filter_item(entry.name, **kwargs):
                paths.append(join_paths(path, entry.name))
    return paths
