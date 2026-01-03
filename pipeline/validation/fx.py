"""FX validation helpers."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from pipeline.spec.model import FX_KEYS

_FX_REQUIRED_FIELDS: Dict[str, Dict[str, str]] = {
    "ROTATE": {"enabled": "bool", "target_z": "int", "speed_dps": "int"},
    "FALL": {"enabled": "bool", "target_z": "int", "speed_pps": "int"},
    "FLOW_X": {
        "enabled": "bool",
        "target_z": "int",
        "speed_pps": "int",
        "range_px": "int",
    },
    "JITTER": {"enabled": "bool", "target_z": "int", "amp_px": "int"},
    "DRIFT": {
        "enabled": "bool",
        "target_z": "int",
        "amp_px": "int",
        "speed_pps": "int",
    },
    "TWINKLE": {"enabled": "bool", "target_z": "int", "period_ms": "int"},
    "FLASH": {"enabled": "bool", "target_z": "int", "period_ms": "int"},
    "CROSSFADE": {"enabled": "bool", "target_z": "int", "period_ms": "int"},
    "NEEDLE": {
        "enabled": "bool",
        "target_z": "int",
        "min_deg": "int",
        "max_deg": "int",
    },
}


def _expect_int(value: Any, name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"fx field {name} must be int")
    return value


def _expect_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"fx field {name} must be bool")
    return value


def _fx_to_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()  # type: ignore[no-any-return]
    if isinstance(value, dict):
        return value
    raise TypeError("invalid fx entry type")


def validate_fx(fx: Dict[str, Any], layer_z: Iterable[int]) -> None:
    for key in FX_KEYS:
        if key not in fx:
            raise ValueError(f"missing fx key: {key}")

    layer_z_set = set(layer_z)
    for key, fields in _FX_REQUIRED_FIELDS.items():
        fx_dict = _fx_to_dict(fx[key])
        for field, expected in fields.items():
            if field not in fx_dict:
                raise ValueError(f"fx {key} missing field: {field}")
            value = fx_dict[field]
            if expected == "int":
                _expect_int(value, f"{key}.{field}")
            elif expected == "bool":
                _expect_bool(value, f"{key}.{field}")

        enabled = _expect_bool(fx_dict["enabled"], f"{key}.enabled")
        target_z = _expect_int(fx_dict["target_z"], f"{key}.target_z")
        if enabled and target_z not in layer_z_set:
            raise ValueError(f"fx {key} target_z does not exist in layers")

        if key in {"FALL", "FLOW_X", "DRIFT"}:
            if fx_dict["speed_pps"] < 0:
                raise ValueError(f"fx {key} speed_pps must be >= 0")
        if key in {"JITTER", "DRIFT"}:
            if fx_dict["amp_px"] < 0:
                raise ValueError(f"fx {key} amp_px must be >= 0")
        if key == "FLOW_X" and fx_dict["range_px"] < 0:
            raise ValueError("fx FLOW_X range_px must be >= 0")
        if key in {"TWINKLE", "FLASH", "CROSSFADE"} and fx_dict["period_ms"] < 0:
            raise ValueError(f"fx {key} period_ms must be >= 0")
        if key == "ROTATE" and fx_dict["speed_dps"] < 0:
            raise ValueError("fx ROTATE speed_dps must be >= 0")
        if key == "NEEDLE":
            if fx_dict["min_deg"] > fx_dict["max_deg"]:
                raise ValueError("fx NEEDLE min_deg must be <= max_deg")
