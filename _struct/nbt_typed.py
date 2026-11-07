"""Type-preserving NBT reader: returns nbt.py tag objects so a read-modify-write round-trips."""
from __future__ import annotations

import gzip
import struct

import nbt

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = 0, 1, 2, 3, 4, 5, 6
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 7, 8, 9, 10, 11, 12


class Reader:
    def __init__(self, data: bytes):
        self.buf = data
        self.i = 0

    def _read(self, n):
        chunk = self.buf[self.i:self.i + n]
        self.i += n
        return chunk

    def u1(self):
        return struct.unpack(">B", self._read(1))[0]

    def i1(self):
        return struct.unpack(">b", self._read(1))[0]

    def i2(self):
        return struct.unpack(">h", self._read(2))[0]

    def i4(self):
        return struct.unpack(">i", self._read(4))[0]

    def i8(self):
        return struct.unpack(">q", self._read(8))[0]

    def f4(self):
        return struct.unpack(">f", self._read(4))[0]

    def f8(self):
        return struct.unpack(">d", self._read(8))[0]

    def string(self):
        n = struct.unpack(">H", self._read(2))[0]
        return self._read(n).decode("utf-8", "replace")

    def payload(self, tag):
        if tag == TAG_BYTE:
            return nbt.Byte(self.i1())
        if tag == TAG_SHORT:
            return nbt.Short(self.i2())
        if tag == TAG_INT:
            return nbt.Int(self.i4())
        if tag == TAG_LONG:
            return nbt.Long(self.i8())
        if tag == TAG_FLOAT:
            return nbt.Float(self.f4())
        if tag == TAG_DOUBLE:
            return nbt.Double(self.f8())
        if tag == TAG_BYTE_ARRAY:
            n = self.i4()
            return nbt.ByteArray(list(self._read(n)))
        if tag == TAG_STRING:
            return nbt.Str(self.string())
        if tag == TAG_LIST:
            elem = self.u1()
            n = self.i4()
            return nbt.ListTag(elem, [self.payload(elem) for _ in range(n)])
        if tag == TAG_COMPOUND:
            out = {}
            while True:
                t = self.u1()
                if t == TAG_END:
                    return nbt.Compound(out)
                name = self.string()
                out[name] = self.payload(t)
        if tag == TAG_INT_ARRAY:
            n = self.i4()
            return nbt.IntArray([self.i4() for _ in range(n)])
        if tag == TAG_LONG_ARRAY:
            n = self.i4()
            return nbt.LongArray([self.i8() for _ in range(n)])
        raise ValueError(f"bad tag {tag}")

    def root(self):
        t = self.u1()
        if t != TAG_COMPOUND:
            raise ValueError("root is not a compound")
        self.string()
        return self.payload(TAG_COMPOUND)


def load(path: str):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return Reader(raw).root()
