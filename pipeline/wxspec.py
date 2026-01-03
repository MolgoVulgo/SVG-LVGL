"""wx.spec v1 JSON generation."""

from __future__ import annotations

import json
from typing import Iterable

from pipeline.spec.model import ASSET_TYPES, FX_KEYS, Asset, Layer, Spec, default_fx
from pipeline.validation.fx import validate_fx
from pipeline.validation.layers import validate_layers


def validate_spec(spec: Spec) -> None:
    if spec.version != "wx.spec.v1":
        raise ValueError("invalid spec version")
    if not spec.id:
        raise ValueError("spec id is required")
    if not spec.assets:
        raise ValueError("spec assets list is empty")
    if not spec.layers:
        raise ValueError("spec layers list is empty")

    assets_by_key = {asset.asset_key: asset for asset in spec.assets}
    for asset in spec.assets:
        if asset.type not in ASSET_TYPES:
            raise ValueError(f"invalid asset type: {asset.type!r}")
        if asset.size_px != spec.size_px:
            raise ValueError("asset size_px must match spec size_px")
        if not (0 <= asset.asset_hash <= 0xFFFFFFFF):
            raise ValueError("asset_hash out of range")

    validate_layers(spec.layers, assets_by_key)
    validate_fx(spec.fx, layer_z=(layer.z for layer in spec.layers))


def ensure_fx_complete(overrides: dict | None = None) -> dict:
    fx = default_fx()
    if overrides:
        fx.update(overrides)
    return fx


def spec_to_dict(spec: Spec) -> dict:
    validate_spec(spec)
    return spec.to_dict()


def dumps_spec(spec: Spec, *, indent: int = 2) -> str:
    return json.dumps(spec_to_dict(spec), indent=indent, sort_keys=False)


def dumps_spec_list(specs: Iterable[Spec], *, indent: int = 2) -> str:
    data = [spec_to_dict(spec) for spec in specs]
    return json.dumps(data, indent=indent, sort_keys=False)


def parse_spec_dict(data: dict) -> Spec:
    if data.get("version") != "wx.spec.v1":
        raise ValueError("invalid spec version")
    if "assets" not in data or "layers" not in data or "fx" not in data:
        raise ValueError("missing required keys in spec")

    assets = []
    for asset_data in data["assets"]:
        assets.append(
            Asset(
                asset_key=asset_data["asset_key"],
                asset_hash=asset_data.get("asset_hash"),
                type=asset_data["type"],
                size_px=asset_data["size_px"],
                path=asset_data["path"],
            )
        )

    layers = []
    for layer_data in data["layers"]:
        layers.append(
            Layer(
                z=layer_data["z"],
                asset_key=layer_data["asset_key"],
                x=layer_data["x"],
                y=layer_data["y"],
                w=layer_data["w"],
                h=layer_data["h"],
                pivot_x=layer_data["pivot_x"],
                pivot_y=layer_data["pivot_y"],
                opacity=layer_data["opacity"],
            )
        )

    fx = ensure_fx_complete()
    fx_data = data["fx"]
    for key in fx_data:
        if key not in FX_KEYS:
            raise ValueError(f"unknown fx key: {key}")
        fx[key] = fx_data[key]

    spec = Spec(
        id=data["id"],
        size_px=data["size_px"],
        assets=assets,
        layers=layers,
        fx=fx,
    )
    validate_spec(spec)
    return spec
