#!/usr/bin/env python3
"""Print only the exception record of a Windows minidump and the module it hit.

Reads the exception stream (code, address, faulting thread) and the module
list; prints the module name and offset for the faulting address. No memory
contents are printed.

Usage: python3 dmpinfo.py file.dmp
"""
import struct
import sys

data = open(sys.argv[1], "rb").read()
if data[:4] != b"MDMP":
    sys.exit("not a minidump")
count, rva = struct.unpack_from("<II", data, 8)
streams = {}
for i in range(count):
    kind, size, off = struct.unpack_from("<III", data, rva + 12 * i)
    streams[kind] = (off, size)


def utf16(off):
    n = struct.unpack_from("<I", data, off)[0]
    return data[off + 4 : off + 4 + n].decode("utf-16-le", "replace")


modules = []
if 4 in streams:  # ModuleListStream
    off, _ = streams[4]
    n = struct.unpack_from("<I", data, off)[0]
    for i in range(n):
        base, size = struct.unpack_from("<QI", data, off + 4 + 108 * i)
        name_rva = struct.unpack_from("<I", data, off + 4 + 108 * i + 20)[0]
        modules.append((base, size, utf16(name_rva).split("\\")[-1]))


def where(address):
    for base, size, name in modules:
        if base <= address < base + size:
            return f"{name}+{address - base:#x}"
    return "outside any loaded module"


if 6 not in streams:  # ExceptionStream
    sys.exit("no exception record")
off, _ = streams[6]
thread = struct.unpack_from("<I", data, off)[0]
code, flags = struct.unpack_from("<II", data, off + 8)
address = struct.unpack_from("<Q", data, off + 24)[0]
nparams = struct.unpack_from("<I", data, off + 32)[0]
params = struct.unpack_from(f"<{min(nparams, 15)}Q", data, off + 40)
print(f"exception code   {code:#010x}")
print(f"faulting thread  {thread:#x}")
print(f"address          {address:#x}  ({where(address)})")
if code == 0xC0000005 and len(params) >= 2:
    kind = {0: "read", 1: "write", 8: "execute"}.get(params[0], str(params[0]))
    print(f"access           {kind} of {params[1]:#x}  ({where(params[1])})")
print(f"modules listed   {len(modules)}")
