"""Asset key normalization and naming conventions."""

import re

_ASSET_KEY_RE = re.compile(r"^[a-z0-9_]+$")


def normalize_asset_key(key: str) -> str:
    """Normalize asset key to [a-z0-9_]+."""
    normalized = key.strip().lower().replace("-", "_")
    if not _ASSET_KEY_RE.match(normalized):
        raise ValueError(f"invalid asset_key: {key!r}")
    return normalized
