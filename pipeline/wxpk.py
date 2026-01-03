"""WXPK v1 pack writer/reader."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

from pipeline.pack.toc import TOC_ENTRY_SIZE, TocEntry
from pipeline.spec.model import Spec
from pipeline.wxspec import dumps_spec, validate_spec

MAGIC = b"WXPK"
VERSION_MAJOR = 1
VERSION_MINOR = 0
HEADER_STRUCT = struct.Struct("<4sHHIIIIII")
HEADER_SIZE = HEADER_STRUCT.size

TYPE_CODES = {"image": 1, "mask": 2, "alpha": 3}


@dataclass
class PackHeader:
    magic: bytes
    version_major: int
    version_minor: int
    toc_count: int
    toc_offset: int
    json_offset: int
    json_size: int
    pack_size: int
    reserved: int = 0

    def to_bytes(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.version_major,
            self.version_minor,
            self.toc_count,
            self.toc_offset,
            self.json_offset,
            self.json_size,
            self.pack_size,
            self.reserved,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "PackHeader":
        if len(raw) != HEADER_SIZE:
            raise ValueError("invalid header size")
        fields = HEADER_STRUCT.unpack(raw)
        return cls(*fields)


def _json_bytes(spec: Spec) -> bytes:
    json_text = dumps_spec(spec, indent=2)
    return json_text.encode("utf-8") + b"\x00"


def build_pack(spec: Spec, payloads: dict[str, bytes]) -> bytes:
    validate_spec(spec)

    toc_entries: list[TocEntry] = []
    payload_blob = bytearray()
    toc_offset = HEADER_SIZE
    toc_count = len(spec.assets)
    payload_offset = toc_offset + toc_count * TOC_ENTRY_SIZE

    for asset in spec.assets:
        payload = payloads.get(asset.asset_key)
        if payload is None:
            raise KeyError(f"missing payload for asset {asset.asset_key!r}")
        type_code = TYPE_CODES.get(asset.type)
        if type_code is None:
            raise ValueError(f"invalid asset type: {asset.type!r}")
        entry = TocEntry(
            asset_hash=asset.asset_hash,
            size_px=asset.size_px,
            type_code=type_code,
            payload_offset=payload_offset,
            payload_size=len(payload),
        )
        toc_entries.append(entry)
        payload_blob.extend(payload)
        payload_offset += len(payload)

    json_data = _json_bytes(spec)
    json_offset = toc_offset + toc_count * TOC_ENTRY_SIZE + len(payload_blob)
    pack_size = json_offset + len(json_data)

    header = PackHeader(
        magic=MAGIC,
        version_major=VERSION_MAJOR,
        version_minor=VERSION_MINOR,
        toc_count=toc_count,
        toc_offset=toc_offset,
        json_offset=json_offset,
        json_size=len(json_data),
        pack_size=pack_size,
    )

    output = bytearray()
    output.extend(header.to_bytes())
    for entry in toc_entries:
        output.extend(entry.to_bytes())
    output.extend(payload_blob)
    output.extend(json_data)
    return bytes(output)


def build_pack_from_files(spec: Spec, root: Path) -> bytes:
    payloads: dict[str, bytes] = {}
    for asset in spec.assets:
        payload_path = root / asset.path
        payloads[asset.asset_key] = payload_path.read_bytes()
    return build_pack(spec, payloads)


def parse_header(data: bytes) -> PackHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError("data too small for header")
    header = PackHeader.from_bytes(data[:HEADER_SIZE])
    if header.magic != MAGIC:
        raise ValueError("invalid WXPK magic")
    if header.version_major != VERSION_MAJOR:
        raise ValueError("unsupported major version")
    if header.pack_size != len(data):
        raise ValueError("pack_size mismatch")
    if header.toc_offset != HEADER_SIZE:
        raise ValueError("unexpected toc_offset")
    if header.json_offset + header.json_size > len(data):
        raise ValueError("json out of bounds")
    return header


def parse_toc(data: bytes, header: PackHeader) -> list[TocEntry]:
    toc_start = header.toc_offset
    toc_end = toc_start + header.toc_count * TOC_ENTRY_SIZE
    if toc_end > len(data):
        raise ValueError("toc out of bounds")
    entries = []
    for idx in range(header.toc_count):
        offset = toc_start + idx * TOC_ENTRY_SIZE
        raw = data[offset : offset + TOC_ENTRY_SIZE]
        entries.append(TocEntry.from_bytes(raw))
    return entries


def extract_json(data: bytes) -> dict:
    header = parse_header(data)
    json_raw = data[header.json_offset : header.json_offset + header.json_size]
    if not json_raw or json_raw[-1] != 0:
        raise ValueError("json not null terminated")
    json_text = json_raw[:-1].decode("utf-8")
    return json.loads(json_text)
