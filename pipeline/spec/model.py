"""In-memory model for wx.spec v1."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional

from pipeline.assets.naming import normalize_asset_key
from pipeline.hash import fnv1a32

SPEC_VERSION = 1

_COMPONENT_RE = re.compile(r"^[A-Z0-9_]+$")
_LAYER_ID_RE = re.compile(r"^[a-z0-9_]+$")

ASSET_TYPES = {"image", "mask", "alpha"}

FX_KEYS = (
    "ROTATE",
    "FALL",
    "FLOW_X",
    "JITTER",
    "DRIFT",
    "TWINKLE",
    "FLASH",
    "CROSSFADE",
    "NEEDLE",
)


def spec_id_for_name(name: str) -> int:
    """Return deterministic spec_id for a normalized name."""
    normalized = normalize_asset_key(name)
    return fnv1a32(normalized)


@dataclass
class Asset:
    asset_key: str
    size_px: int
    path: str
    type: str = "image"
    asset_hash: int | None = None

    def __post_init__(self) -> None:
        self.asset_key = normalize_asset_key(self.asset_key)
        if self.type not in ASSET_TYPES:
            raise ValueError(f"invalid asset type: {self.type!r}")
        computed = fnv1a32(self.asset_key)
        if self.asset_hash is None:
            self.asset_hash = computed
        elif self.asset_hash != computed:
            raise ValueError("asset_hash does not match asset_key")

    def to_dict(self) -> dict:
        return {
            "asset_key": self.asset_key,
            "asset_hash": self.asset_hash,
            "type": self.type,
            "size_px": self.size_px,
            "path": self.path,
        }


@dataclass
class Components:
    decor: str
    cover: str
    particles: str
    atmos: str
    event: str

    def __post_init__(self) -> None:
        for field_name in ("decor", "cover", "particles", "atmos", "event"):
            value = getattr(self, field_name)
            if not _COMPONENT_RE.match(value):
                raise ValueError(f"invalid component {field_name}: {value!r}")

    def to_dict(self) -> dict:
        return {
            "decor": self.decor,
            "cover": self.cover,
            "particles": self.particles,
            "atmos": self.atmos,
            "event": self.event,
        }


@dataclass
class LayerSpec:
    layer_id: str
    asset: str
    fx: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.layer_id = normalize_asset_key(self.layer_id)
        self.asset = normalize_asset_key(self.asset)
        if not _LAYER_ID_RE.match(self.layer_id):
            raise ValueError(f"invalid layer id: {self.layer_id!r}")

    def to_dict(self) -> dict:
        return {
            "id": self.layer_id,
            "asset": self.asset,
            "fx": list(self.fx),
        }


@dataclass
class Metadata:
    version: int = SPEC_VERSION
    created_by: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict:
        data = {"version": self.version}
        if self.created_by is not None:
            data["created_by"] = self.created_by
        if self.confidence is not None:
            data["confidence"] = self.confidence
        return data


def _fx_to_dict(fx_value: object) -> dict:
    if hasattr(fx_value, "to_dict"):
        return fx_value.to_dict()  # type: ignore[no-any-return]
    if isinstance(fx_value, dict):
        return fx_value
    raise TypeError("invalid fx value type")


@dataclass
class Spec:
    spec_id: Optional[int]
    name: str
    components: Components
    assets: List[Asset] = field(default_factory=list)
    layers: List[LayerSpec] = field(default_factory=list)
    fx: Dict[str, object] = field(default_factory=dict)
    metadata: Metadata = field(default_factory=Metadata)

    def __post_init__(self) -> None:
        self.name = normalize_asset_key(self.name)
        expected_id = spec_id_for_name(self.name)
        if self.spec_id is None:
            self.spec_id = expected_id
        if not (0 <= int(self.spec_id) <= 0xFFFFFFFF):
            raise ValueError("spec_id out of range")
        if int(self.spec_id) != expected_id:
            raise ValueError("spec_id does not match name")

    def to_dict(self) -> dict:
        if self.metadata.version != SPEC_VERSION:
            raise ValueError("invalid spec metadata version")

        return {
            "spec_id": int(self.spec_id),
            "name": self.name,
            "components": self.components.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "fx": {key: _fx_to_dict(self.fx[key]) for key in self.fx},
            "metadata": self.metadata.to_dict(),
        }


def asset_keys(assets: Iterable[Asset]) -> List[str]:
    return [asset.asset_key for asset in assets]
