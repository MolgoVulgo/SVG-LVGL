"""FX validation helpers."""

from __future__ import annotations

from typing import Any, Dict

from pipeline.spec.model import FX_KEYS

_ALLOWED_FIELDS = {
    "period_ms",
    "pivot_x",
    "pivot_y",
    "angle_from",
    "angle_to",
    "angle_now",
    "smooth_ms",
    "fall_dx",
    "fall_dy",
    "amp_x",
    "amp_y",
    "opa_min",
    "opa_max",
    "phase_ms",
}


def _fx_to_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()  # type: ignore[no-any-return]
    if isinstance(value, dict):
        return value
    raise TypeError("invalid fx entry type")


def _expect_int(value: Any, name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"fx field {name} must be int")
    return value


def _expect_float(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"fx field {name} must be float")
    return float(value)


def validate_fx(fx: Dict[str, Any]) -> None:
    for key in fx:
        if key not in FX_KEYS:
            raise ValueError(f"unknown fx key: {key}")

        fx_dict = _fx_to_dict(fx[key])
        for field, value in fx_dict.items():
            if field not in _ALLOWED_FIELDS:
                raise ValueError(f"fx {key} unknown field: {field}")
            if field == "phase_ms":
                if not isinstance(value, list):
                    raise ValueError(f"fx {key}.phase_ms must be list")
                if len(value) > 6:
                    raise ValueError("fx phase_ms length must be <= 6")
                for idx, item in enumerate(value):
                    if not isinstance(item, int) or item < 0:
                        raise ValueError(f"fx {key}.phase_ms[{idx}] must be int >= 0")
                continue

            if field in {"opa_min", "opa_max"}:
                val = _expect_int(value, f"{key}.{field}")
                if not (0 <= val <= 255):
                    raise ValueError(f"fx {key}.{field} must be 0..255")
                continue

            if field in {"angle_from", "angle_to", "angle_now"}:
                val = _expect_int(value, f"{key}.{field}")
                if not (0 <= val <= 3600):
                    raise ValueError(f"fx {key}.{field} must be 0..3600")
                continue

            if field in {"period_ms", "pivot_x", "pivot_y", "smooth_ms"}:
                val = _expect_int(value, f"{key}.{field}")
                if val < 0:
                    raise ValueError(f"fx {key}.{field} must be >= 0")
                continue

            if field in {"fall_dx", "fall_dy", "amp_x", "amp_y"}:
                val = _expect_int(value, f"{key}.{field}")
                if val < 0:
                    raise ValueError(f"fx {key}.{field} must be >= 0")
                continue

            _expect_float(value, f"{key}.{field}")
