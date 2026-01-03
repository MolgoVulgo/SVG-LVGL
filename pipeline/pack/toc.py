"""TOC structure for WXPK v1."""

from __future__ import annotations

from dataclasses import dataclass
import struct

TOC_STRUCT = struct.Struct("<IHHIIIII")
TOC_ENTRY_SIZE = TOC_STRUCT.size


@dataclass
class TocEntry:
    asset_hash: int
    size_px: int
    type_code: int
    payload_offset: int
    payload_size: int
    reserved0: int = 0
    reserved1: int = 0
    reserved2: int = 0

    def to_bytes(self) -> bytes:
        return TOC_STRUCT.pack(
            self.asset_hash,
            self.size_px,
            self.type_code,
            self.payload_offset,
            self.payload_size,
            self.reserved0,
            self.reserved1,
            self.reserved2,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "TocEntry":
        if len(raw) != TOC_ENTRY_SIZE:
            raise ValueError("invalid TOC entry size")
        fields = TOC_STRUCT.unpack(raw)
        return cls(*fields)
