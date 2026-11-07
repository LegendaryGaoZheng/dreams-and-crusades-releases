"""Minimal NBT reader (big-endian, gzip-aware) for inspecting structure templates."""
from __future__ import annotations

import gzip
import io
import struct

TAG_END = 0
TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = 1, 2, 3, 4, 5, 6
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 7, 8, 9, 10, 11, 12


class Reader:
    def __init__(self, data: bytes):
        self.buf = io.BytesIO(data)

    def u1(self):
        return struct.unpack(">B", self.buf.read(1))[0]

    def i1(self):
        return struct.unpack(">b", self.buf.read(1))[0]

    def i2(self):
        return struct.unpack(">h", self.buf.read(2))[0]

    def i4(self):
        return struct.unpack(">i", self.buf.read(4))[0]

    def i8(self):
        return struct.unpack(">q", self.buf.read(8))[0]

    def f4(self):
        return struct.unpack(">f", self.buf.read(4))[0]

    def f8(self):
        return struct.unpack(">d", self.buf.read(8))[0]

    def string(self):
        n = struct.unpack(">H", self.buf.read(2))[0]
        return self.buf.read(n).decode("utf-8", "replace")

    def payload(self, tag):
        if tag == TAG_BYTE:
            return self.i1()
        if tag == TAG_SHORT:
            return self.i2()
        if tag == TAG_INT:
            return self.i4()
        if tag == TAG_LONG:
            return self.i8()
        if tag == TAG_FLOAT:
            return self.f4()
        if tag == TAG_DOUBLE:
            return self.f8()
        if tag == TAG_BYTE_ARRAY:
            n = self.i4()
            return list(self.buf.read(n))
        if tag == TAG_STRING:
            return self.string()
        if tag == TAG_LIST:
            elem = self.u1()
            n = self.i4()
            return [self.payload(elem) for _ in range(n)]
        if tag == TAG_COMPOUND:
            out = {}
            while True:
                t = self.u1()
                if t == TAG_END:
                    return out
                name = self.string()
                out[name] = self.payload(t)
        if tag == TAG_INT_ARRAY:
            n = self.i4()
            return [self.i4() for _ in range(n)]
        if tag == TAG_LONG_ARRAY:
            n = self.i4()
            return [self.i8() for _ in range(n)]
        raise ValueError(f"bad tag {tag}")

    def root(self):
        t = self.u1()
        if t != TAG_COMPOUND:
            raise ValueError("root is not a compound")
        self.string()
        return self.payload(TAG_COMPOUND)


def load(path: str) -> dict:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return Reader(raw).root()


def structure_blocks(root: dict):
    """Yield (x, y, z, block_id, props) for every block entry."""
    palette = root.get("palette", [])
    for entry in root.get("blocks", []):
        pos = entry["pos"]
        state = entry["state"]
        pal = palette[state] if state < len(palette) else {}
        yield pos[0], pos[1], pos[2], pal.get("Name", "?"), pal.get("Properties", {})
