"""Minimal NBT writer (big-endian, gzip) — enough for Minecraft structure templates.

Data model:
    Byte/Short/Int/Long/Float/Double/Str  -> scalar wrappers
    ListTag(tag_type, items)              -> TAG_List
    Compound(dict)                        -> TAG_Compound   (plain dict also works)
    IntArray(list) / LongArray / ByteArray
"""
from __future__ import annotations

import gzip
import struct

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = 0, 1, 2, 3, 4, 5, 6
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 7, 8, 9, 10, 11, 12


class _Scalar:
    tag = None

    def __init__(self, value):
        self.value = value


class Byte(_Scalar):
    tag = TAG_BYTE


class Short(_Scalar):
    tag = TAG_SHORT


class Int(_Scalar):
    tag = TAG_INT


class Long(_Scalar):
    tag = TAG_LONG


class Float(_Scalar):
    tag = TAG_FLOAT


class Double(_Scalar):
    tag = TAG_DOUBLE


class Str(_Scalar):
    tag = TAG_STRING


class ListTag:
    tag = TAG_LIST

    def __init__(self, tag_type, items):
        self.tag_type = tag_type
        self.items = list(items)


class Compound:
    tag = TAG_COMPOUND

    def __init__(self, mapping=None):
        self.value = dict(mapping or {})


class IntArray:
    tag = TAG_INT_ARRAY

    def __init__(self, values):
        self.value = list(values)


class LongArray:
    tag = TAG_LONG_ARRAY

    def __init__(self, values):
        self.value = list(values)


class ByteArray:
    tag = TAG_BYTE_ARRAY

    def __init__(self, values):
        self.value = list(values)


def _write_payload(out: bytearray, tag: _Scalar):
    if tag.tag == TAG_BYTE:
        out += struct.pack(">b", int(tag.value))
    elif tag.tag == TAG_SHORT:
        out += struct.pack(">h", int(tag.value))
    elif tag.tag == TAG_INT:
        out += struct.pack(">i", int(tag.value))
    elif tag.tag == TAG_LONG:
        out += struct.pack(">q", int(tag.value))
    elif tag.tag == TAG_FLOAT:
        out += struct.pack(">f", float(tag.value))
    elif tag.tag == TAG_DOUBLE:
        out += struct.pack(">d", float(tag.value))
    elif tag.tag == TAG_STRING:
        raw = str(tag.value).encode("utf-8")
        out += struct.pack(">H", len(raw)) + raw
    else:  # pragma: no cover
        raise TypeError(f"unsupported scalar tag {tag.tag}")


def _write_named(out: bytearray, name: str, value):
    raw_name = name.encode("utf-8")
    if isinstance(value, Compound) or isinstance(value, dict):
        out += struct.pack(">b", TAG_COMPOUND) + struct.pack(">H", len(raw_name)) + raw_name
        mapping = value.value if isinstance(value, Compound) else value
        _write_compound_body(out, mapping)
        return
    if isinstance(value, ListTag):
        out += struct.pack(">b", TAG_LIST) + struct.pack(">H", len(raw_name)) + raw_name
        out += struct.pack(">b", value.tag_type) + struct.pack(">i", len(value.items))
        for item in value.items:
            _write_payload_body(out, item)
        return
    if isinstance(value, IntArray):
        out += struct.pack(">b", TAG_INT_ARRAY) + struct.pack(">H", len(raw_name)) + raw_name
        out += struct.pack(">i", len(value.value))
        for v in value.value:
            out += struct.pack(">i", int(v))
        return
    if isinstance(value, (LongArray, ByteArray)):
        raise TypeError("array tags not needed here")
    if isinstance(value, bool):
        value = Byte(1 if value else 0)
    if isinstance(value, str):
        value = Str(value)
    if isinstance(value, int):
        value = Int(value)
    if isinstance(value, float):
        value = Double(value)
    if not isinstance(value, _Scalar):
        raise TypeError(f"cannot serialise {type(value)!r} for key {name!r}")
    out += struct.pack(">b", value.tag) + struct.pack(">H", len(raw_name)) + raw_name
    _write_payload(out, value)


def _write_payload_body(out: bytearray, item):
    if isinstance(item, Compound) or isinstance(item, dict):
        _write_compound_body(out, item.value if isinstance(item, Compound) else item)
    elif isinstance(item, _Scalar):
        _write_payload(out, item)
    elif isinstance(item, ListTag):
        out += struct.pack(">b", item.tag_type) + struct.pack(">i", len(item.items))
        for sub in item.items:
            _write_payload_body(out, sub)
    else:
        raise TypeError(f"cannot serialise list item {type(item)!r}")


def _write_compound_body(out: bytearray, mapping):
    for key, value in mapping.items():
        _write_named(out, str(key), value)
    out += struct.pack(">b", TAG_END)


def dumps(root_mapping) -> bytes:
    """Serialise a root compound to uncompressed NBT bytes (with root tag header)."""
    out = bytearray()
    out += struct.pack(">b", TAG_COMPOUND) + struct.pack(">H", 0)   # tag + empty root name
    _write_compound_body(out, root_mapping)
    return bytes(out)


def save(root_mapping, path):
    """Write gzip-compressed NBT (structure template format)."""
    payload = dumps(root_mapping)
    with open(path, "wb") as fh:
        fh.write(gzip.compress(payload, 9))
    return len(payload)
