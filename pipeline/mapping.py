"""SVG pattern mapping to runtime wx.spec v1 objects."""

from __future__ import annotations

from pathlib import Path

from pipeline.assets.naming import normalize_asset_key
from pipeline.hash import fnv1a32
from pipeline.spec.model import Components, LayerSpec, Spec
from pipeline.svg.parse import SvgDocument, parse_svg
from pipeline.wxspec import validate_spec


def _derive_spec_name(svg: SvgDocument, svg_path: Path, explicit: str | None) -> str:
    raw = explicit or svg.spec_id or svg_path.stem
    return normalize_asset_key(raw)


def _unique_layer_id(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    index = 1
    while True:
        candidate = f"{base}_{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _layers_from_svg(svg: SvgDocument) -> list[LayerSpec]:
    layers: list[LayerSpec] = []
    used_ids: set[str] = set()
    for raw in sorted(svg.layers, key=lambda layer: layer.z):
        base_id = normalize_asset_key(raw.asset_key)
        layer_id = _unique_layer_id(base_id, used_ids)
        layers.append(
            LayerSpec(
                layer_id=layer_id,
                asset=base_id,
                fx=[],
            )
        )
    return layers


def _default_layer_for_svg(spec_name: str) -> list[LayerSpec]:
    return [
        LayerSpec(
            layer_id=spec_name,
            asset=spec_name,
            fx=[],
        )
    ]


def map_svg_to_spec(
    svg_path: Path,
    *,
    spec_id: str | None = None,
    size_px: int | None = None,
) -> Spec:
    svg = parse_svg(svg_path)
    resolved_name = _derive_spec_name(svg, svg_path, spec_id)
    resolved_size = size_px or svg.width or svg.height
    if resolved_size is None:
        raise ValueError("size_px not provided and SVG size not found")

    layers = _layers_from_svg(svg)
    if not layers:
        layers = _default_layer_for_svg(resolved_name)
    if not layers:
        raise ValueError("no layers found in SVG")

    fx = {}
    fx_targets = {}
    for key, raw in svg.fx.items():
        if not isinstance(raw, dict):
            continue
        target_z = raw.get("target_z")
        fx_targets[key] = target_z
        cleaned = {k: v for k, v in raw.items() if k not in {"enabled", "target_z"}}
        fx[key] = cleaned

    if fx_targets:
        for key, target_z in fx_targets.items():
            if target_z is None and len(layers) == 1:
                layers[0].fx.append(key)
                continue
            for raw_layer in svg.layers:
                if raw_layer.z == target_z:
                    index = sorted(svg.layers, key=lambda layer: layer.z).index(raw_layer)
                    layers[index].fx.append(key)
                    break

    used_fx = {fx_key for layer in layers for fx_key in layer.fx}
    fx = {key: fx.get(key, {}) for key in used_fx}

    spec = Spec(
        spec_id=fnv1a32(resolved_name),
        name=resolved_name,
        components=Components(
            decor="NONE",
            cover="NONE",
            particles="NONE",
            atmos="NONE",
            event="NONE",
        ),
        layers=layers,
        fx=fx,
    )
    validate_spec(spec)
    return spec
