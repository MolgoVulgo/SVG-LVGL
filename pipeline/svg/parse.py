"""SVG parsing entry points."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import re

from pipeline.spec.model import FX_KEYS


@dataclass
class SvgLayer:
    z: int
    asset_key: str
    x: int
    y: int
    w: int | None
    h: int | None
    pivot_x: int | None
    pivot_y: int | None
    opacity: int


@dataclass
class SvgDocument:
    width: int | None
    height: int | None
    layers: list[SvgLayer]
    fx: dict
    spec_id: str | None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.endswith("px"):
        cleaned = cleaned[:-2]
    try:
        return int(float(cleaned))
    except ValueError as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def _parse_viewbox(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    parts = value.replace(",", " ").split()
    if len(parts) != 4:
        return None, None
    try:
        width = int(float(parts[2]))
        height = int(float(parts[3]))
    except ValueError:
        return None, None
    return width, height


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _auto_asset_key(raw: str | None, index: int) -> str:
    if raw:
        cleaned = re.sub(r"[^a-z0-9_]+", "_", raw.strip().lower().replace("-", "_"))
        cleaned = cleaned.strip("_")
        if cleaned:
            return cleaned
    return f"layer_{index}"


def _is_in_defs(elem: ET.Element, parents: dict[ET.Element, ET.Element]) -> bool:
    current = elem
    while current is not None:
        if _strip_ns(current.tag) == "defs":
            return True
        current = parents.get(current)
    return False


def _parse_duration_ms(value: str | None) -> float | None:
    if value is None:
        return None
    raw = value.strip()
    try:
        if raw.endswith("ms"):
            return float(raw[:-2])
        if raw.endswith("s"):
            return float(raw[:-1]) * 1000.0
        return float(raw) * 1000.0
    except ValueError as exc:
        raise ValueError(f"invalid duration: {value!r}") from exc


def _parse_values_pair(values: str) -> tuple[str, str] | None:
    parts = [part.strip() for part in values.split(";") if part.strip()]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def _parse_rotate_delta(
    values: str | None, from_value: str | None, to_value: str | None
) -> tuple[float | None, tuple[int, int] | None]:
    def _parse_rotate(value: str) -> tuple[float, tuple[int, int] | None]:
        parts = value.replace(",", " ").split()
        if not parts:
            raise ValueError("invalid rotate value")
        angle = float(parts[0])
        pivot = None
        if len(parts) >= 3:
            pivot = (int(float(parts[1])), int(float(parts[2])))
        return angle, pivot

    if values:
        pair = _parse_values_pair(values)
        if not pair:
            return None, None
        first, second = pair
        try:
            start, pivot_a = _parse_rotate(first)
            end, pivot_b = _parse_rotate(second)
            pivot = pivot_a or pivot_b
            return abs(end - start), pivot
        except (IndexError, ValueError) as exc:
            raise ValueError("invalid rotate values") from exc
    if from_value and to_value:
        try:
            start, pivot_a = _parse_rotate(from_value)
            end, pivot_b = _parse_rotate(to_value)
            pivot = pivot_a or pivot_b
            return abs(end - start), pivot
        except ValueError as exc:
            raise ValueError("invalid rotate from/to") from exc
    return None, None


def _parse_translate_delta(values: str | None, from_value: str | None, to_value: str | None) -> tuple[float, float] | None:
    def _parse_pair(value: str) -> tuple[float, float]:
        parts = value.replace(",", " ").split()
        if len(parts) < 2:
            raise ValueError("invalid translate pair")
        return float(parts[0]), float(parts[1])

    if values:
        pair = _parse_values_pair(values)
        if not pair:
            return None
        first, second = pair
        x0, y0 = _parse_pair(first)
        x1, y1 = _parse_pair(second)
        return x1 - x0, y1 - y0
    if from_value and to_value:
        x0, y0 = _parse_pair(from_value)
        x1, y1 = _parse_pair(to_value)
        return x1 - x0, y1 - y0
    return None


def _find_target_z(
    elem: ET.Element,
    parents: dict[ET.Element, ET.Element],
    element_z: dict[ET.Element, int],
) -> int | None:
    current = elem
    while current is not None:
        if current in element_z:
            return element_z[current]
        z_raw = current.attrib.get("data-wx-z")
        if z_raw is not None:
            z = _parse_int(z_raw)
            if z is None:
                raise ValueError("data-wx-z must be an integer")
            return int(z)
        current = parents.get(current)
    return None


def _parse_fx(root: ET.Element) -> dict:
    fx = {}
    for key in FX_KEYS:
        raw = root.attrib.get(f"data-wx-fx-{key}")
        if not raw:
            continue
        try:
            fx[key] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid fx json for {key}") from exc
    return fx


def _parse_fx_from_animations(
    root: ET.Element,
    parents: dict[ET.Element, ET.Element],
    element_z: dict[ET.Element, int],
    existing_fx: dict,
) -> dict:
    fx = dict(existing_fx)
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag == "animateTransform":
            transform_type = elem.attrib.get("type")
            duration_ms = _parse_duration_ms(elem.attrib.get("dur"))
            target_z = _find_target_z(elem, parents, element_z)
            if transform_type == "rotate" and "ROTATE" not in fx:
                delta, pivot = _parse_rotate_delta(
                    elem.attrib.get("values"),
                    elem.attrib.get("from"),
                    elem.attrib.get("to"),
                )
                if duration_ms and duration_ms > 0 and delta is not None:
                    rotate_fx = {
                        "period_ms": int(round(duration_ms)),
                        "target_z": target_z or 0,
                    }
                    if pivot is not None:
                        rotate_fx["pivot_x"] = pivot[0]
                        rotate_fx["pivot_y"] = pivot[1]
                    fx["ROTATE"] = rotate_fx
            elif transform_type == "translate":
                delta = _parse_translate_delta(
                    elem.attrib.get("values"),
                    elem.attrib.get("from"),
                    elem.attrib.get("to"),
                )
                if duration_ms and duration_ms > 0 and delta is not None:
                    dx, dy = delta
                    if abs(dy) >= abs(dx):
                        if "FALL" not in fx:
                            fx["FALL"] = {
                                "period_ms": int(round(duration_ms)),
                                "target_z": target_z or 0,
                                "fall_dy": int(round(abs(dy))),
                            }
                    else:
                        if "FLOW_X" not in fx:
                            fx["FLOW_X"] = {
                                "period_ms": int(round(duration_ms)),
                                "target_z": target_z or 0,
                                "amp_x": int(round(abs(dx))),
                    }
        elif tag == "animate":
            if elem.attrib.get("attributeName") == "opacity" and "TWINKLE" not in fx:
                duration_ms = _parse_duration_ms(elem.attrib.get("dur"))
                target_z = _find_target_z(elem, parents, element_z)
                if duration_ms and duration_ms > 0:
                    fx["TWINKLE"] = {
                        "period_ms": int(round(duration_ms)),
                        "target_z": target_z or 0,
                    }
    return fx


def parse_svg(path: Path) -> SvgDocument:
    tree = ET.parse(path)
    root = tree.getroot()

    spec_id = root.attrib.get("data-wx-id") or root.attrib.get("id")

    width = _parse_int(root.attrib.get("width"))
    height = _parse_int(root.attrib.get("height"))
    if width is None or height is None:
        vb_w, vb_h = _parse_viewbox(root.attrib.get("viewBox"))
        width = width or vb_w
        height = height or vb_h

    parents: dict[ET.Element, ET.Element] = {}
    for elem in root.iter():
        for child in list(elem):
            parents[child] = elem

    layers: list[SvgLayer] = []
    element_z: dict[ET.Element, int] = {}
    has_explicit_layers = False
    for elem in root.iter():
        if _is_in_defs(elem, parents):
            continue
        asset_key = elem.attrib.get("data-wx-asset")
        z_raw = elem.attrib.get("data-wx-z")
        if asset_key is None or z_raw is None:
            continue
        has_explicit_layers = True
        z = _parse_int(z_raw)
        if z is None:
            raise ValueError("data-wx-z must be an integer")

        layer = SvgLayer(
            z=int(z),
            asset_key=asset_key,
            x=_parse_int(elem.attrib.get("data-wx-x")) or 0,
            y=_parse_int(elem.attrib.get("data-wx-y")) or 0,
            w=_parse_int(elem.attrib.get("data-wx-w")),
            h=_parse_int(elem.attrib.get("data-wx-h")),
            pivot_x=_parse_int(elem.attrib.get("data-wx-pivot-x")),
            pivot_y=_parse_int(elem.attrib.get("data-wx-pivot-y")),
            opacity=_parse_int(elem.attrib.get("data-wx-opacity")) or 255,
        )
        layers.append(layer)
        element_z[elem] = int(z)

    if not has_explicit_layers:
        drawable_tags = {
            "path",
            "circle",
            "rect",
            "ellipse",
            "line",
            "polyline",
            "polygon",
            "g",
        }
        index = 0
        for elem in root.iter():
            if _is_in_defs(elem, parents):
                continue
            tag = _strip_ns(elem.tag)
            if tag not in drawable_tags:
                continue
            asset_key = _auto_asset_key(elem.attrib.get("id"), index)
            layer = SvgLayer(
                z=index,
                asset_key=asset_key,
                x=0,
                y=0,
                w=None,
                h=None,
                pivot_x=None,
                pivot_y=None,
                opacity=255,
            )
            layers.append(layer)
            element_z[elem] = index
            index += 1
    fx = _parse_fx(root)
    fx = _parse_fx_from_animations(root, parents, element_z, fx)
    return SvgDocument(width=width, height=height, layers=layers, fx=fx, spec_id=spec_id)
