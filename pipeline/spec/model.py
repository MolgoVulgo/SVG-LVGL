"""In-memory model for wx.spec v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from pipeline.assets.naming import normalize_asset_key
from pipeline.hash import fnv1a32

SPEC_VERSION = "wx.spec.v1"

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
class Layer:
    z: int
    asset_key: str
    x: int
    y: int
    w: int
    h: int
    pivot_x: int
    pivot_y: int
    opacity: int

    def __post_init__(self) -> None:
        self.asset_key = normalize_asset_key(self.asset_key)
        if not (0 <= self.opacity <= 255):
            raise ValueError("opacity must be 0..255")

    def to_dict(self) -> dict:
        return {
            "z": self.z,
            "asset_key": self.asset_key,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "pivot_x": self.pivot_x,
            "pivot_y": self.pivot_y,
            "opacity": self.opacity,
        }


@dataclass
class FxRotate:
    enabled: bool
    target_z: int
    speed_dps: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "speed_dps": self.speed_dps,
        }


@dataclass
class FxFall:
    enabled: bool
    target_z: int
    speed_pps: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "speed_pps": self.speed_pps,
        }


@dataclass
class FxFlowX:
    enabled: bool
    target_z: int
    speed_pps: int
    range_px: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "speed_pps": self.speed_pps,
            "range_px": self.range_px,
        }


@dataclass
class FxJitter:
    enabled: bool
    target_z: int
    amp_px: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "amp_px": self.amp_px,
        }


@dataclass
class FxDrift:
    enabled: bool
    target_z: int
    amp_px: int
    speed_pps: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "amp_px": self.amp_px,
            "speed_pps": self.speed_pps,
        }


@dataclass
class FxTwinkle:
    enabled: bool
    target_z: int
    period_ms: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "period_ms": self.period_ms,
        }


@dataclass
class FxFlash:
    enabled: bool
    target_z: int
    period_ms: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "period_ms": self.period_ms,
        }


@dataclass
class FxCrossfade:
    enabled: bool
    target_z: int
    period_ms: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "period_ms": self.period_ms,
        }


@dataclass
class FxNeedle:
    enabled: bool
    target_z: int
    min_deg: int
    max_deg: int

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_z": self.target_z,
            "min_deg": self.min_deg,
            "max_deg": self.max_deg,
        }


def default_fx() -> Dict[str, object]:
    return {
        "ROTATE": FxRotate(False, 0, 0),
        "FALL": FxFall(False, 0, 0),
        "FLOW_X": FxFlowX(False, 0, 0, 0),
        "JITTER": FxJitter(False, 0, 0),
        "DRIFT": FxDrift(False, 0, 0, 0),
        "TWINKLE": FxTwinkle(False, 0, 0),
        "FLASH": FxFlash(False, 0, 0),
        "CROSSFADE": FxCrossfade(False, 0, 0),
        "NEEDLE": FxNeedle(False, 0, 0, 0),
    }


def _fx_to_dict(fx_value: object) -> dict:
    if hasattr(fx_value, "to_dict"):
        return fx_value.to_dict()  # type: ignore[no-any-return]
    if isinstance(fx_value, dict):
        return fx_value
    raise TypeError("invalid fx value type")


@dataclass
class Spec:
    id: str
    size_px: int
    assets: List[Asset] = field(default_factory=list)
    layers: List[Layer] = field(default_factory=list)
    fx: Dict[str, object] = field(default_factory=default_fx)
    version: str = SPEC_VERSION

    def to_dict(self) -> dict:
        if self.version != SPEC_VERSION:
            raise ValueError("invalid spec version")

        fx_keys = set(self.fx.keys())
        missing = [key for key in FX_KEYS if key not in fx_keys]
        if missing:
            raise ValueError(f"missing fx keys: {missing}")

        return {
            "version": self.version,
            "id": self.id,
            "size_px": self.size_px,
            "assets": [asset.to_dict() for asset in self.assets],
            "layers": [layer.to_dict() for layer in self.layers],
            "fx": {key: _fx_to_dict(self.fx[key]) for key in FX_KEYS},
        }


def asset_keys(assets: Iterable[Asset]) -> List[str]:
    return [asset.asset_key for asset in assets]
