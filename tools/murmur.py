"""Stingray resource name hash (MurmurHash64A, seed 0)."""

MASK = 0xFFFFFFFFFFFFFFFF


def murmur64(data: bytes, seed: int = 0) -> int:
    m = 0xC6A4A7935BD1E995
    r = 47
    h = (seed ^ (len(data) * m)) & MASK
    n = len(data) // 8
    for i in range(n):
        k = int.from_bytes(data[i * 8:i * 8 + 8], "little")
        k = (k * m) & MASK
        k ^= k >> r
        k = (k * m) & MASK
        h ^= k
        h = (h * m) & MASK
    tail = data[n * 8:]
    if tail:
        h ^= int.from_bytes(tail, "little")
        h = (h * m) & MASK
    h ^= h >> r
    h = (h * m) & MASK
    h ^= h >> r
    return h
