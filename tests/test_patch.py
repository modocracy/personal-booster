"""Check that tools/patch.py rebuilds published mod archives byte for byte.

Uses Booster Buster (one resource per archive) and Vanilla Plus Megapack (two per
archive) unpacked under extracted/ (see README); skips the ones that are missing.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from murmur import murmur64  # noqa: E402
import patch  # noqa: E402

HEADER = re.compile(rb"^-- HD2-Addon: (mods/[A-Za-z0-9_]+/[A-Za-z0-9_/]+)")


def archives(folder):
    return glob.glob(os.path.join(ROOT, "extracted", folder, "**", "*.patch_0"), recursive=True)


def main():
    single, multi = archives("booster_buster"), archives("megapack")
    if not single and not multi:
        print("SKIP: extracted/booster_buster and extracted/megapack are missing")
        return 0
    for path in single:
        original = open(path, "rb").read()
        name_hash, source = patch.read(original)
        name = HEADER.match(source).group(1).decode()
        assert murmur64(name.encode()) == name_hash, path
        assert patch.build(name, source) == original, path
    for path in multi:
        original = open(path, "rb").read()
        entries = patch.read_all(original)
        assert len(entries) > 1, path
        assert patch.build_many(entries, pad_end=True) == original, path
    print(f"OK: {len(single)} single-resource and {len(multi)} two-resource archives rebuilt identically")
    return 0


if __name__ == "__main__":
    sys.exit(main())
