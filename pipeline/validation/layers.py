"""Layer validation helpers."""

from __future__ import annotations

from typing import Iterable, Set

from pipeline.spec.model import FX_KEYS, LayerSpec


def validate_layers(layers: Iterable[LayerSpec], fx_keys: Set[str]) -> None:
    ids_seen = set()
    for layer in layers:
        if layer.layer_id in ids_seen:
            raise ValueError(f"duplicate layer id: {layer.layer_id}")
        ids_seen.add(layer.layer_id)
        for fx_key in layer.fx:
            if fx_key not in FX_KEYS:
                raise ValueError(f"layer fx unknown: {fx_key}")
            if fx_key not in fx_keys:
                raise ValueError(f"layer fx missing spec config: {fx_key}")
