"""Layer validation helpers."""

from __future__ import annotations

from typing import Dict, Iterable

from pipeline.spec.model import Layer


def validate_layers(layers: Iterable[Layer], assets_by_key: Dict[str, object]) -> None:
    z_seen = set()
    for layer in layers:
        if layer.asset_key not in assets_by_key:
            raise ValueError(f"layer asset_key missing: {layer.asset_key!r}")
        if layer.z in z_seen:
            raise ValueError(f"duplicate layer z: {layer.z}")
        z_seen.add(layer.z)
        if layer.w <= 0 or layer.h <= 0:
            raise ValueError("layer w/h must be > 0")
        if not (0 <= layer.pivot_x <= layer.w):
            raise ValueError("layer pivot_x out of bounds")
        if not (0 <= layer.pivot_y <= layer.h):
            raise ValueError("layer pivot_y out of bounds")
        if not (0 <= layer.opacity <= 255):
            raise ValueError("layer opacity must be 0..255")
