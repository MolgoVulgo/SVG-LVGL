"""WXPK v1 pack writer/reader."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
import zlib

from pipeline.pack.toc import TOC_ENTRY_SIZE, TocEntry
from pipeline.spec.model import Asset, Spec
from pipeline.wxspec import dumps_spec, validate_spec

MAGIC = 0x4B505857
VERSION = 1
ENDIAN_LITTLE = 0
HEADER_STRUCT = struct.Struct("<I H B B I I I I I I")
HEADER_SIZE = HEADER_STRUCT.size

WXPK_T_IMG = 1
WXPK_T_JSON_INDEX = 2
WXPK_T_JSON_SPEC = 3
WXPK_T_JSON_ALL = 4

WXPK_C_NONE = 0
WXPK_C_LVGL_BIN = 1
WXPK_C_PNG = 2
WXPK_C_RAW_RGBA8888 = 3

_ASSET_DEFAULT_CODEC = WXPK_C_LVGL_BIN


@dataclass
class PackHeader:
    magic: int
    version: int
    endian: int
    header_size: int
    flags: int
    toc_offset: int
    toc_count: int
    blobs_offset: int
    file_crc32: int
    reserved: int = 0

    def to_bytes(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.version,
            self.endian,
            self.header_size,
            self.flags,
            self.toc_offset,
            self.toc_count,
            self.blobs_offset,
            self.file_crc32,
            self.reserved,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "PackHeader":
        if len(raw) != HEADER_SIZE:
            raise ValueError("invalid header size")
        fields = HEADER_STRUCT.unpack(raw)
        return cls(*fields)


def _align_up(value: int, alignment: int = 4) -> int:
    if alignment <= 0:
        return value
    return (value + alignment - 1) // alignment * alignment


def _json_bytes(spec: Spec) -> bytes:
    json_text = dumps_spec(spec, indent=2)
    return json_text.encode("utf-8")


def _asset_codec(asset: Asset) -> int:
    return _ASSET_DEFAULT_CODEC


def build_pack(specs: list[Spec], assets: list[Asset], payloads: dict[str, bytes]) -> bytes:
    if not specs:
        raise ValueError("specs list is empty")

    for spec in specs:
        validate_spec(spec)

    toc_entries: list[TocEntry] = []
    blobs: list[bytes] = []

    toc_offset = HEADER_SIZE
    toc_count = len(assets) + len(specs)
    blobs_offset = _align_up(toc_offset + toc_count * TOC_ENTRY_SIZE, 4)
    current_offset = blobs_offset

    for asset in assets:
        payload = payloads.get(asset.asset_key)
        if payload is None:
            raise KeyError(f"missing payload for asset {asset.asset_key!r}")
        codec = _asset_codec(asset)
        crc32 = zlib.crc32(payload) & 0xFFFFFFFF
        toc_entries.append(
            TocEntry(
                key_hash=int(asset.asset_hash),
                type_code=WXPK_T_IMG,
                codec=codec,
                size_px=asset.size_px,
                offset=current_offset,
                length=len(payload),
                crc32=crc32,
                meta=0,
            )
        )
        blobs.append(payload)
        current_offset = _align_up(current_offset + len(payload), 4)

    for spec in specs:
        json_data = _json_bytes(spec)
        crc32 = zlib.crc32(json_data) & 0xFFFFFFFF
        toc_entries.append(
            TocEntry(
                key_hash=int(spec.spec_id),
                type_code=WXPK_T_JSON_SPEC,
                codec=WXPK_C_NONE,
                size_px=0,
                offset=current_offset,
                length=len(json_data),
                crc32=crc32,
                meta=0,
            )
        )
        blobs.append(json_data)
        current_offset = _align_up(current_offset + len(json_data), 4)

    header = PackHeader(
        magic=MAGIC,
        version=VERSION,
        endian=ENDIAN_LITTLE,
        header_size=HEADER_SIZE,
        flags=0,
        toc_offset=toc_offset,
        toc_count=toc_count,
        blobs_offset=blobs_offset,
        file_crc32=0,
    )

    output = bytearray()
    output.extend(header.to_bytes())
    for entry in toc_entries:
        output.extend(entry.to_bytes())
    if len(output) < blobs_offset:
        output.extend(b"\x00" * (blobs_offset - len(output)))

    for blob in blobs:
        output.extend(blob)
        padded = _align_up(len(output), 4)
        if padded != len(output):
            output.extend(b"\x00" * (padded - len(output)))

    return bytes(output)


def build_pack_from_files(specs: list[Spec], assets: list[Asset], root: Path) -> bytes:
    payloads: dict[str, bytes] = {}
    for asset in assets:
        payload_path = root / asset.path
        payloads[asset.asset_key] = payload_path.read_bytes()
    return build_pack(specs, assets, payloads)


def parse_header(data: bytes) -> PackHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError("data too small for header")
    header = PackHeader.from_bytes(data[:HEADER_SIZE])
    if header.magic != MAGIC:
        raise ValueError("invalid WXPK magic")
    if header.version != VERSION:
        raise ValueError("unsupported pack version")
    if header.endian != ENDIAN_LITTLE:
        raise ValueError("unsupported endian")
    if header.header_size != HEADER_SIZE:
        raise ValueError("unexpected header_size")
    if header.toc_offset < HEADER_SIZE:
        raise ValueError("invalid toc_offset")
    if header.blobs_offset < header.toc_offset + header.toc_count * TOC_ENTRY_SIZE:
        raise ValueError("invalid blobs_offset")
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


def find_entry(entries: list[TocEntry], key_hash: int, type_code: int, size_px: int) -> TocEntry | None:
    for entry in entries:
        if (
            entry.key_hash == key_hash
            and entry.type_code == type_code
            and entry.size_px == size_px
        ):
            return entry
    return None


def extract_json_spec(data: bytes, spec_id: int) -> dict:
    header = parse_header(data)
    entries = parse_toc(data, header)
    entry = find_entry(entries, spec_id, WXPK_T_JSON_SPEC, 0)
    if entry is None:
        raise ValueError("spec_id not found in pack")
    json_raw = data[entry.offset : entry.offset + entry.length]
    json_text = json_raw.decode("utf-8")
    return json.loads(json_text)
