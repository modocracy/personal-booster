"""Write and read Helldivers 2 patch archives holding Lua resources (9ba626afa44a3aa3.patch_0).

Layout: a 0x48-byte header (magic, type count, file count, total size at 0x20), one
type entry (lua), one 0x50-byte file entry per resource, then each resource at a
16-byte boundary. A Lua resource is u32 length, u32 2, then the source or bytecode.
"""

import struct

from murmur import murmur64

MAGIC = 0xF0000011
LUA_TYPE = murmur64(b"lua")
HEADER, TYPE_ENTRY, FILE_ENTRY, ALIGN = 0x48, 0x20, 0x50, 0x10


def lua_resource(body: bytes) -> bytes:
    return struct.pack("<II", len(body), 2) + body


def _aligned(offset):
    return (offset + ALIGN - 1) // ALIGN * ALIGN


def build_many(entries, pad_end=False) -> bytes:
    """entries: (resource name or name hash, Lua body). Returns the archive."""
    hashes = [murmur64(n.encode()) if isinstance(n, str) else n for n, _ in entries]
    payloads = [lua_resource(body) for _, body in entries]
    offsets, at = [], _aligned(HEADER + TYPE_ENTRY + FILE_ENTRY * len(entries))
    for payload in payloads:
        offsets.append(at)
        at = _aligned(at + len(payload))
    total = at if pad_end else offsets[-1] + len(payloads[-1])

    out = bytearray(total)
    struct.pack_into("<III", out, 0, MAGIC, 1, len(entries))
    struct.pack_into("<I", out, 0x20, total)
    struct.pack_into("<QII", out, HEADER + 8, LUA_TYPE, len(entries), 0)
    struct.pack_into("<II", out, HEADER + 0x18, ALIGN, ALIGN)
    for index, (name_hash, offset, payload) in enumerate(zip(hashes, offsets, payloads)):
        entry = HEADER + TYPE_ENTRY + FILE_ENTRY * index
        struct.pack_into("<QQQ", out, entry, name_hash, LUA_TYPE, offset)
        struct.pack_into("<I", out, entry + 0x38, len(payload))
        struct.pack_into("<III", out, entry + 0x44, ALIGN, ALIGN, index)
        out[offset:offset + len(payload)] = payload
    return bytes(out)


def build(resource_name: str, source: bytes) -> bytes:
    return build_many([(resource_name, source)])


def read_all(data: bytes):
    """[(name_hash, body)] of every Lua resource in an archive."""
    magic, types, files = struct.unpack_from("<III", data, 0)
    if magic != MAGIC or types != 1:
        raise ValueError("not a Lua patch archive")
    out = []
    for index in range(files):
        entry = HEADER + TYPE_ENTRY + FILE_ENTRY * index
        name_hash, type_hash, offset = struct.unpack_from("<QQQ", data, entry)
        if type_hash != LUA_TYPE:
            raise ValueError("entry is not Lua")
        length, _ = struct.unpack_from("<II", data, offset)
        out.append((name_hash, data[offset + 8:offset + 8 + length]))
    return out


def read(data: bytes):
    """(name_hash, body) from a single-Lua patch archive."""
    entries = read_all(data)
    if len(entries) != 1:
        raise ValueError("not a single-Lua patch archive")
    return entries[0]
