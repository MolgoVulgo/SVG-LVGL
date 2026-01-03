"""SVG pattern mapping to runtime wx.spec v1 objects."""

from __future__ import annotations

from pathlib import Path

from pipeline.assets.naming import normalize_asset_key
from pipeline.spec.model import Asset, Layer, Spec
from pipeline.svg.parse import SvgDocument, parse_svg
from pipeline.wxspec import ensure_fx_complete, validate_spec


def _default_layer_w(size_px: int) -> int:
    return size_px


def _default_layer_h(size_px: int) -> int:
    return size_px


def _default_pivot(value: int) -> int:
    return value // 2


def _asset_path(asset_key: str, size_px: int) -> str:
    return f"{asset_key}_{size_px}.bin"


def _layers_from_svg(svg: SvgDocument, size_px: int) -> list[Layer]:
    layers: list[Layer] = []
    for raw in svg.layers:
        w = raw.w if raw.w is not None else _default_layer_w(size_px)
        h = raw.h if raw.h is not None else _default_layer_h(size_px)
        pivot_x = raw.pivot_x if raw.pivot_x is not None else _default_pivot(w)
        pivot_y = raw.pivot_y if raw.pivot_y is not None else _default_pivot(h)
        layers.append(
            Layer(
                z=raw.z,
                asset_key=raw.asset_key,
                x=raw.x,
                y=raw.y,
                w=w,
                h=h,
                pivot_x=pivot_x,
                pivot_y=pivot_y,
                opacity=raw.opacity,
            )
        )
    return layers


def _assets_from_layers(layers: list[Layer], size_px: int) -> list[Asset]:
    assets: dict[str, Asset] = {}
    for layer in layers:
        if layer.asset_key in assets:
            continue
        assets[layer.asset_key] = Asset(
            asset_key=layer.asset_key,
            size_px=size_px,
            type="image",
            path=_asset_path(layer.asset_key, size_px),
        )
    return list(assets.values())


def _derive_spec_id(svg: SvgDocument, svg_path: Path, explicit: str | None) -> str:
    raw = explicit or svg.spec_id or svg_path.stem
    return normalize_asset_key(raw)


def _default_layer_for_svg(spec_id: str, size_px: int) -> list[Layer]:
    return [
        Layer(
            z=0,
            asset_key=spec_id,
            x=0,
            y=0,
            w=size_px,
            h=size_px,
            pivot_x=size_px // 2,
            pivot_y=size_px // 2,
            opacity=255,
        )
    ]


def map_svg_to_spec(
    svg_path: Path,
    *,
    spec_id: str | None = None,
    size_px: int | None = None,
) -> Spec:
    svg = parse_svg(svg_path)
    resolved_id = _derive_spec_id(svg, svg_path, spec_id)
    resolved_size = size_px or svg.width or svg.height
    if resolved_size is None:
        raise ValueError("size_px not provided and SVG size not found")

    layers = _layers_from_svg(svg, resolved_size)
    if not layers:
        layers = _default_layer_for_svg(resolved_id, resolved_size)
    if not layers:
        raise ValueError("no layers found in SVG")

    assets = _assets_from_layers(layers, resolved_size)
    fx = ensure_fx_complete(svg.fx)

    spec = Spec(id=resolved_id, size_px=resolved_size, assets=assets, layers=layers, fx=fx)
    validate_spec(spec)
    return spec
