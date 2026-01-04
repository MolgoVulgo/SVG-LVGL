"""TOC structure for WXPK v1."""

from __future__ import annotations

from dataclasses import dataclass
import struct

TOC_STRUCT = struct.Struct("<IBBHIIII")
TOC_ENTRY_SIZE = TOC_STRUCT.size + 4


@dataclass
class TocEntry:
    key_hash: int
    type_code: int
    codec: int
    size_px: int
    offset: int
    length: int
    crc32: int
    meta: int = 0
    reserved: int = 0

    def to_bytes(self) -> bytes:
        packed = TOC_STRUCT.pack(
            self.key_hash,
            self.type_code,
            self.codec,
            self.size_px,
            self.offset,
            self.length,
            self.crc32,
            self.meta,
        )
        return packed + struct.pack("<I", self.reserved)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "TocEntry":
        if len(raw) != TOC_ENTRY_SIZE:
            raise ValueError("invalid TOC entry size")
        fields = TOC_STRUCT.unpack(raw[: TOC_STRUCT.size])
        reserved = struct.unpack("<I", raw[TOC_STRUCT.size : TOC_ENTRY_SIZE])[0]
        return cls(*fields, reserved=reserved)
