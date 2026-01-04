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
    asset_ref: str | None
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


def _use_href(elem: ET.Element) -> str | None:
    href = elem.attrib.get("href")
    if href is None:
        href = elem.attrib.get("{http://www.w3.org/1999/xlink}href")
    if href is None:
        href = elem.attrib.get("xlink:href")
    if href is None:
        return None
    return href.lstrip("#")


def _paint_href(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw.startswith("url("):
        return None
    if "#" not in raw:
        return None
    ref = raw.split("#", 1)[1].rstrip(")")
    return ref.strip()


def _resolve_paint_id(paint: str | None, id_map: dict[str, ET.Element]) -> str | None:
    ref = _paint_href(paint)
    if not ref:
        return None
    current = id_map.get(ref)
    visited: set[str] = set()
    while current is not None:
        current_id = current.attrib.get("id")
        if not current_id or current_id in visited:
            break
        visited.add(current_id)
        href = _use_href(current)
        if not href:
            return current_id
        current = id_map.get(href)
    return ref


def _signature_for_element(
    elem: ET.Element,
    id_map: dict[str, ET.Element],
) -> tuple | None:
    tag = _strip_ns(elem.tag)
    if tag == "line":
        try:
            x1 = float(elem.attrib.get("x1", "0"))
            y1 = float(elem.attrib.get("y1", "0"))
            x2 = float(elem.attrib.get("x2", "0"))
            y2 = float(elem.attrib.get("y2", "0"))
        except ValueError:
            return None
        dx = round(x2 - x1, 3)
        dy = round(y2 - y1, 3)
        stroke_width = elem.attrib.get("stroke-width")
        stroke_linecap = elem.attrib.get("stroke-linecap")
        stroke_miter = elem.attrib.get("stroke-miterlimit")
        paint_id = _resolve_paint_id(elem.attrib.get("stroke"), id_map)
        return (
            "line",
            dx,
            dy,
            stroke_width,
            stroke_linecap,
            stroke_miter,
            paint_id,
        )
    return None


def _is_drawable_target(
    elem: ET.Element,
    drawable_tags: set[str],
    id_map: dict[str, ET.Element],
    visited: set[ET.Element],
) -> bool:
    if elem in visited:
        return False
    visited.add(elem)
    tag = _strip_ns(elem.tag)
    if tag not in drawable_tags:
        return False
    if tag == "use":
        ref = _use_href(elem)
        if not ref:
            return False
        target = id_map.get(ref)
        if target is None:
            return False
        return _is_drawable_target(target, drawable_tags, id_map, visited)
    if tag == "g":
        for child in list(elem):
            if _is_drawable_target(child, drawable_tags, id_map, visited):
                return True
        return False
    if tag == "path":
        return bool(elem.attrib.get("d"))
    if tag == "circle":
        return "r" in elem.attrib
    if tag == "ellipse":
        return "rx" in elem.attrib and "ry" in elem.attrib
    if tag == "rect":
        return "width" in elem.attrib and "height" in elem.attrib
    if tag == "line":
        return all(k in elem.attrib for k in ("x1", "y1", "x2", "y2"))
    if tag in {"polyline", "polygon"}:
        return "points" in elem.attrib
    return True


def _is_drawable_element(
    elem: ET.Element,
    parents: dict[ET.Element, ET.Element],
    drawable_tags: set[str],
    id_map: dict[str, ET.Element],
) -> bool:
    if _is_in_defs(elem, parents):
        return False
    tag = _strip_ns(elem.tag)
    if tag not in drawable_tags:
        return False
    if tag == "use":
        ref = _use_href(elem)
        if not ref:
            return False
        target = id_map.get(ref)
        if target is None:
            return False
        return _is_drawable_target(target, drawable_tags, id_map, set())
    if tag == "g":
        for child in list(elem):
            if _is_drawable_element(child, parents, drawable_tags, id_map):
                return True
        return False
    if tag == "path":
        return bool(elem.attrib.get("d"))
    if tag == "circle":
        return "r" in elem.attrib
    if tag == "ellipse":
        return "rx" in elem.attrib and "ry" in elem.attrib
    if tag == "rect":
        return "width" in elem.attrib and "height" in elem.attrib
    if tag == "line":
        return all(k in elem.attrib for k in ("x1", "y1", "x2", "y2"))
    if tag in {"polyline", "polygon"}:
        return "points" in elem.attrib
    return True


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
            asset_ref=None,
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
            "use",
        }
        id_map = {elem.attrib["id"]: elem for elem in root.iter() if "id" in elem.attrib}
        signature_map: dict[tuple, str] = {}
        index = 0
        for elem in root.iter():
            if not _is_drawable_element(elem, parents, drawable_tags, id_map):
                continue
            tag = _strip_ns(elem.tag)
            if tag == "use":
                ref_id = _use_href(elem)
                if ref_id and ref_id in id_map:
                    asset_key = _auto_asset_key(ref_id, index)
                else:
                    asset_key = _auto_asset_key(elem.attrib.get("id"), index)
            else:
                asset_key = _auto_asset_key(elem.attrib.get("id"), index)
            asset_ref = None
            signature = _signature_for_element(elem, id_map)
            if signature is not None:
                existing = signature_map.get(signature)
                if existing:
                    asset_ref = existing
                else:
                    signature_map[signature] = asset_key
            layer = SvgLayer(
                z=index,
                asset_key=asset_key,
                asset_ref=asset_ref,
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
