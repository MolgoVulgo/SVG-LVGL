"""wx.spec v1 JSON generation."""

from __future__ import annotations

import json
from typing import Iterable

from pipeline.spec.model import Components, FX_KEYS, LayerSpec, Metadata, Spec, spec_id_for_name
from pipeline.validation.fx import validate_fx
from pipeline.validation.layers import validate_layers


def validate_spec(spec: Spec) -> None:
    if spec.spec_id is None:
        raise ValueError("spec_id is required")
    if spec.spec_id != spec_id_for_name(spec.name):
        raise ValueError("spec_id does not match name")
    if not spec.layers:
        raise ValueError("spec layers list is empty")
    if spec.metadata.version != 1:
        raise ValueError("metadata.version must be 1")
    if spec.metadata.confidence is not None:
        if not (0.0 <= spec.metadata.confidence <= 1.0):
            raise ValueError("metadata.confidence must be 0..1")

    validate_fx(spec.fx)
    validate_layers(spec.layers, fx_keys=set(spec.fx.keys()))


def spec_to_dict(spec: Spec) -> dict:
    validate_spec(spec)
    return spec.to_dict()


def dumps_spec(spec: Spec, *, indent: int = 2) -> str:
    return json.dumps(spec_to_dict(spec), indent=indent, sort_keys=False)


def dumps_spec_list(specs: Iterable[Spec], *, indent: int = 2) -> str:
    data = [spec_to_dict(spec) for spec in specs]
    return json.dumps(data, indent=indent, sort_keys=False)


def parse_spec_dict(data: dict) -> Spec:
    required = {"spec_id", "name", "components", "layers", "fx", "metadata"}
    if not required.issubset(set(data.keys())):
        raise ValueError("missing required keys in spec")

    components = data["components"]
    component = Components(
        decor=components["decor"],
        cover=components["cover"],
        particles=components["particles"],
        atmos=components["atmos"],
        event=components["event"],
    )

    layers = []
    for layer_data in data["layers"]:
        layers.append(
            LayerSpec(
                layer_id=layer_data["id"],
                asset=layer_data["asset"],
                fx=list(layer_data.get("fx", [])),
            )
        )

    fx = {}
    fx_data = data["fx"]
    for key, value in fx_data.items():
        if key not in FX_KEYS:
            raise ValueError(f"unknown fx key: {key}")
        fx[key] = value

    metadata = data["metadata"]
    meta = Metadata(
        version=metadata.get("version", 0),
        created_by=metadata.get("created_by"),
        confidence=metadata.get("confidence"),
    )

    spec = Spec(
        spec_id=data["spec_id"],
        name=data["name"],
        components=component,
        layers=layers,
        fx=fx,
        metadata=meta,
    )
    validate_spec(spec)
    return spec
