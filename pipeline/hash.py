"""Hash helpers."""

from __future__ import annotations


def fnv1a32(text: str) -> int:
    """Return FNV1a32 hash for ASCII asset_key."""
    h = 0x811C9DC5
    for b in text.encode("ascii"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h
