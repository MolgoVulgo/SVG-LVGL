"""Qt GUI for inspecting/editing wx.spec v1 JSON."""

from __future__ import annotations

import base64
import io
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.mapping import map_svg_to_spec
from pipeline.wxspec import dumps_spec, parse_spec_dict

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception as exc:  # pragma: no cover - import guard
    raise RuntimeError("PySide6 + QtWebEngine required for gui-qt") from exc


class WxSpecQtGui(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WX Spec Inspector (Qt)")
        self.resize(1100, 720)

        self._current_path: Path | None = None
        self._current_svg: Path | None = None
        self._current_spec: dict | None = None
        self._svg_raster_cache: dict[tuple[int, int | None], bytes] = {}
        self._svg_root: ET.Element | None = None
        self._svg_paths: list[tuple[int, ...]] = []
        self._svg_anim_map: dict[int, set[str]] = {}
        self._asset_bitmaps: dict[str, "Image.Image"] = {}
        self._frame_timer = QtCore.QTimer(self)
        self._frame_timer.setInterval(33)
        self._frame_timer.timeout.connect(self._animate_frame)
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        self._frame_bytes: bytes | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QtWidgets.QToolBar("Main")
        self.addToolBar(toolbar)

        open_svg_action = QtGui.QAction("Open SVG", self)
        open_svg_action.triggered.connect(self._open_svg)
        toolbar.addAction(open_svg_action)

        save_action = QtGui.QAction("Save JSON", self)
        save_action.triggered.connect(self._save_json)
        toolbar.addAction(save_action)

        refresh_action = QtGui.QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh)
        toolbar.addAction(refresh_action)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)

        self._svg_source_label = QtWidgets.QLabel("SVG source")
        left_layout.addWidget(self._svg_source_label, stretch=0)
        self._svg_source = QtWidgets.QPlainTextEdit()
        self._svg_source.setReadOnly(True)
        self._svg_source.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        left_layout.addWidget(self._svg_source, stretch=3)

        self._json_label = QtWidgets.QLabel("JSON")
        left_layout.addWidget(self._json_label, stretch=0)
        self._text = QtWidgets.QPlainTextEdit()
        self._text.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        left_layout.addWidget(self._text, stretch=2)

        splitter.addWidget(left)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(6, 6, 6, 6)

        self._deps_box = QtWidgets.QGroupBox("Dependencies")
        deps_layout = QtWidgets.QFormLayout(self._deps_box)
        self._deps_label = QtWidgets.QLabel()
        deps_layout.addRow(self._deps_label)
        right_layout.addWidget(self._deps_box, stretch=0)

        self._tabs = QtWidgets.QTabWidget()
        right_layout.addWidget(self._tabs, stretch=2)

        self._svg_tab = QtWidgets.QWidget()
        self._svg_layout = QtWidgets.QVBoxLayout(self._svg_tab)
        self._svg_view = QWebEngineView()
        self._svg_layout.addWidget(self._svg_view)
        self._tabs.addTab(self._svg_tab, "SVG")

        self._assets_tab = QtWidgets.QWidget()
        self._assets_layout = QtWidgets.QVBoxLayout(self._assets_tab)
        self._assets_scroll = QtWidgets.QScrollArea()
        self._assets_scroll.setWidgetResizable(True)
        self._assets_container = QtWidgets.QWidget()
        self._assets_grid = QtWidgets.QGridLayout(self._assets_container)
        self._assets_scroll.setWidget(self._assets_container)
        self._assets_layout.addWidget(self._assets_scroll)
        self._tabs.addTab(self._assets_tab, "Assets")

        self._final_tab = QtWidgets.QWidget()
        self._final_layout = QtWidgets.QVBoxLayout(self._final_tab)
        self._final_label = QtWidgets.QLabel("Final preview")
        self._final_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._final_layout.addWidget(self._final_label)
        self._tabs.addTab(self._final_tab, "Final")

        self._tabs.currentChanged.connect(self._refresh)

        fx_box = QtWidgets.QGroupBox("FX Enabled")
        fx_layout = QtWidgets.QVBoxLayout(fx_box)
        self._fx_list = QtWidgets.QListWidget()
        fx_layout.addWidget(self._fx_list)
        right_layout.addWidget(fx_box, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._update_dependencies()

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text, 4000)

    def _open_svg(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open SVG", "", "SVG files (*.svg);;All files (*)"
        )
        if not path:
            return
        svg_path = Path(path)
        try:
            spec = map_svg_to_spec(svg_path)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "SVG conversion failed", str(exc))
            return
        self._current_svg = svg_path
        self._svg_raster_cache.clear()
        self._prepare_svg_layers(svg_path)
        self._current_path = None
        self._svg_source.setPlainText(svg_path.read_text(encoding="utf-8"))
        self._text.setPlainText(dumps_spec(spec, indent=2))
        self._refresh()

    def _save_json(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save JSON", "", "JSON files (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            spec = parse_spec_dict(self._parse_text())
            Path(path).write_text(dumps_spec(spec, indent=2), encoding="utf-8")
            self._status(f"Saved {path}")
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def _parse_text(self) -> dict:
        raw = self._text.toPlainText().strip()
        if not raw:
            raise ValueError("JSON text is empty")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("root JSON must be an object")
        return data

    def _refresh(self) -> None:
        try:
            spec = parse_spec_dict(self._parse_text())
            self._current_spec = spec.to_dict()
        except Exception as exc:  # noqa: BLE001
            self._current_spec = None
            self._status(f"Error: {exc}")
            return

        self._fx_list.clear()
        fx = self._current_spec.get("fx", {})
        for layer in self._spec_layers():
            for key in layer.get("fx", []):
                if key in fx:
                    self._fx_list.addItem(f"{key} -> {layer['id']}")

        tab = self._tabs.tabText(self._tabs.currentIndex()).lower()
        if tab == "svg":
            self._render_svg()
        elif tab == "assets":
            self._render_assets()
        elif tab == "final":
            self._render_final()

    def _render_svg(self) -> None:
        if not self._current_svg:
            self._svg_view.setHtml("<html><body>No SVG loaded.</body></html>")
            return
        svg_text = self._current_svg.read_text(encoding="utf-8")
        html = (
            "<html><head><style>"
            "body{margin:0;background:#fff;}svg{width:100%;height:100%;}"
            "</style></head><body>"
            f"{svg_text}"
            "</body></html>"
        )
        self._svg_view.setHtml(html)

    def _render_assets(self) -> None:
        self._clear_grid(self._assets_grid)
        if not self._current_spec:
            return
        assets_root = self._resolve_assets_root()
        row = 0
        col = 0
        layer_map = self._layer_index_map()
        for asset in self._spec_assets():
            asset_key = asset["asset_key"]
            pixmap = self._load_asset_pixmap(
                assets_root, asset, layer_map.get(asset_key)
            )
            if pixmap is None:
                continue
            label = QtWidgets.QLabel()
            label.setPixmap(pixmap)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            text = QtWidgets.QLabel(asset_key)
            text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cell = QtWidgets.QVBoxLayout()
            cell_widget = QtWidgets.QWidget()
            cell.addWidget(label)
            cell.addWidget(text)
            cell_widget.setLayout(cell)
            self._assets_grid.addWidget(cell_widget, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        if row == 0 and col == 0:
            self._assets_grid.addWidget(QtWidgets.QLabel("No PNG+alpha assets found."), 0, 0)

    def _render_final(self) -> None:
        if not _ensure_pillow():
            self._final_label.setText("Final preview requires Pillow (PIL).")
            return
        self._prepare_asset_bitmaps()
        if not self._asset_bitmaps:
            self._final_label.setText("No PNG+alpha assets found.")
            return
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        self._frame_timer.start()

    def _animate_frame(self) -> None:
        if not self._current_spec:
            self._frame_timer.stop()
            return
        size_px = self._resolve_size_px()
        if size_px <= 0:
            return
        scale = 320 / size_px

        now = time.time()
        self._last_frame_time = now
        elapsed = now - self._start_time

        from PIL import Image

        canvas = Image.new("RGBA", (int(size_px), int(size_px)), (0, 0, 0, 0))
        layers = self._spec_layers()
        assets = {asset["asset_key"]: asset for asset in self._spec_assets()}
        layer_map = self._layer_index_map()
        fx = self._current_spec.get("fx", {})

        for layer in layers:
            base = self._asset_bitmaps.get(layer["asset"])
            if base is None:
                idx = layer_map.get(layer["asset"])
                if idx is not None:
                    fallback = self._get_svg_raster(size_px, idx)
                    if fallback is not None:
                        base = _load_pil_image(fallback)
            if base is None:
                continue
            img = base
            offset_x = 0.0
            offset_y = 0.0
            opacity = 1.0
            rotation = 0.0

            for key in layer.get("fx", []):
                value = fx.get(key, {})
                if not isinstance(value, dict):
                    continue
                idx = layer_map.get(layer["asset"])
                anim_types = self._svg_anim_map.get(idx, set())
                if key == "ROTATE" and "rotate" not in anim_types and idx is not None:
                    continue
                if key in {"FALL", "FLOW_X"} and "translate" not in anim_types and idx is not None:
                    continue
                if key in {"TWINKLE", "FLASH", "CROSSFADE"} and "opacity" not in anim_types and idx is not None:
                    continue

                period_ms = float(value.get("period_ms", 0) or 0)
                period = period_ms / 1000.0 if period_ms > 0 else 0.0
                amp_x = float(value.get("amp_x", 0) or 0)
                amp_y = float(value.get("amp_y", 0) or 0)
                opa_min = float(value.get("opa_min", 0) or 0) / 255.0
                opa_max = float(value.get("opa_max", 255) or 255) / 255.0
                if key == "ROTATE" and period > 0:
                    rotation = (elapsed / period) * 360.0
                elif key == "FALL" and period > 0:
                    fall_dy = float(value.get("fall_dy", 0) or 0)
                    offset_y = (elapsed / period) * fall_dy
                elif key == "FLOW_X" and period > 0:
                    offset_x = (elapsed / period) * amp_x
                elif key == "JITTER":
                    offset_x += random.uniform(-amp_x, amp_x)
                    offset_y += random.uniform(-amp_y, amp_y)
                elif key == "DRIFT" and period > 0:
                    offset_x += math.sin(elapsed * 2 * math.pi / period) * amp_x
                    offset_y += math.cos(elapsed * 2 * math.pi / period) * amp_y
                elif key == "TWINKLE" and period > 0:
                    wave = 0.5 + 0.5 * math.sin(elapsed * 2 * math.pi / period)
                    opacity *= opa_min + wave * (opa_max - opa_min)
                elif key == "FLASH" and period > 0:
                    phase = elapsed % period
                    opacity *= opa_max if phase < (period / 2) else opa_min
                elif key == "CROSSFADE" and period > 0:
                    wave = 0.5 + 0.5 * math.cos(elapsed * 2 * math.pi / period)
                    opacity *= opa_min + wave * (opa_max - opa_min)

            img, pivot_offset = _apply_transform_with_pivot(
                img,
                rotation,
                opacity,
                float(img.width / 2),
                float(img.height / 2),
            )
            pivot_x = float(img.width / 2)
            pivot_y = float(img.height / 2)
            draw_x = int(offset_x + pivot_x - pivot_offset[0])
            draw_y = int(offset_y + pivot_y - pivot_offset[1])
            canvas.alpha_composite(img, (draw_x, draw_y))

        frame = canvas.resize((int(size_px * scale), int(size_px * scale)))
        self._frame_bytes = frame.tobytes("raw", "RGBA")
        qimg = QtGui.QImage(
            self._frame_bytes,
            frame.width,
            frame.height,
            QtGui.QImage.Format.Format_RGBA8888,
        )
        self._final_label.setPixmap(QtGui.QPixmap.fromImage(qimg))

    def _resolve_assets_root(self) -> Path:
        if self._current_path is not None:
            return self._current_path.parent
        if self._current_svg is not None:
            return self._current_svg.parent
        return Path.cwd()

    def _default_asset_path(self, asset_key: str, size_px: int) -> str:
        return f"{asset_key}_{size_px}.png"

    def _spec_layers(self) -> list[dict]:
        if not self._current_spec:
            return []
        layers = self._current_spec.get("layers", [])
        normalized = []
        for layer in layers:
            asset_key = layer.get("asset") or layer.get("asset_key")
            if not asset_key:
                continue
            normalized.append(
                {
                    "id": layer.get("id") or asset_key,
                    "asset": asset_key,
                    "fx": list(layer.get("fx", [])),
                }
            )
        return normalized

    def _spec_assets(self) -> list[dict]:
        if not self._current_spec:
            return []
        if "assets" in self._current_spec:
            return list(self._current_spec.get("assets", []))
        size_px = self._resolve_size_px()
        assets: dict[str, dict] = {}
        for layer in self._spec_layers():
            key = layer["asset"]
            if key in assets:
                continue
            assets[key] = {
                "asset_key": key,
                "size_px": size_px,
                "path": self._default_asset_path(key, size_px),
            }
        return list(assets.values())

    def _resolve_size_px(self) -> int:
        if not self._current_spec:
            return 64
        size_px = int(self._current_spec.get("size_px", 0) or 0)
        if size_px > 0:
            return size_px
        if self._current_svg:
            inferred = self._infer_svg_size(self._current_svg)
            if inferred:
                return inferred
        return 64

    @staticmethod
    def _infer_svg_size(svg_path: Path) -> int | None:
        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            return None
        root = tree.getroot()
        width = root.attrib.get("width")
        height = root.attrib.get("height")
        for raw in (width, height):
            if raw is None:
                continue
            cleaned = raw.strip()
            if cleaned.endswith("px"):
                cleaned = cleaned[:-2]
            try:
                return int(float(cleaned))
            except ValueError:
                continue
        view_box = root.attrib.get("viewBox")
        if view_box:
            parts = view_box.replace(",", " ").split()
            if len(parts) == 4:
                try:
                    return int(float(parts[2]))
                except ValueError:
                    return None
        return None

    def _load_asset_pixmap(
        self, root: Path, asset: dict, layer_index: int | None
    ) -> QtGui.QPixmap | None:
        path = root / asset.get("path", "")
        if path.exists():
            data = path.read_bytes()
            if _png_has_alpha(data):
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(data)
                return pixmap
        data = self._get_svg_raster(
            int(asset.get("size_px", 0)) or self._resolve_size_px(),
            layer_index,
        )
        if data is None:
            return None
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        return pixmap

    def _prepare_asset_bitmaps(self) -> None:
        assets_root = self._resolve_assets_root()
        assets = self._spec_assets()
        self._asset_bitmaps.clear()
        layer_map = self._layer_index_map()
        for asset in assets:
            path = assets_root / asset.get("path", "")
            if path.exists():
                data = path.read_bytes()
                if _png_has_alpha(data):
                    image = _load_pil_image(data)
                    if image is not None:
                        self._asset_bitmaps[asset["asset_key"]] = image
                    continue
            idx = layer_map.get(asset["asset_key"])
            fallback = self._get_svg_raster(
                int(asset.get("size_px", 0)) or self._resolve_size_px(),
                idx,
            )
            if fallback is None:
                continue
            image = _load_pil_image(fallback)
            if image is not None:
                self._asset_bitmaps[asset["asset_key"]] = image

    def _get_svg_raster(self, size_px: int, index: int | None) -> bytes | None:
        if not self._current_svg:
            return None
        key = (size_px, index)
        cached = self._svg_raster_cache.get(key)
        if cached:
            return cached
        if index is None:
            png_bytes = _render_svg_png(self._current_svg, size_px)
        else:
            png_bytes = self._render_svg_element(index, size_px)
        if png_bytes is None:
            return None
        self._svg_raster_cache[key] = png_bytes
        return png_bytes

    def _prepare_svg_layers(self, svg_path: Path) -> None:
        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            self._svg_root = None
            self._svg_paths = []
            return
        root = tree.getroot()
        parents = {child: parent for parent in root.iter() for child in list(parent)}
        id_map = {elem.attrib["id"]: elem for elem in root.iter() if "id" in elem.attrib}
        drawable = {
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
        paths: list[tuple[int, ...]] = []
        anim_map: dict[int, set[str]] = {}

        def _strip_ns(tag: str) -> str:
            return tag.split("}", 1)[1] if "}" in tag else tag

        def _path_to(elem: ET.Element) -> tuple[int, ...]:
            parts = []
            current = elem
            while current is not root:
                parent = parents[current]
                parts.append(list(parent).index(current))
                current = parent
            return tuple(reversed(parts))

        def _is_in_defs(elem: ET.Element) -> bool:
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

        def _is_drawable_target(elem: ET.Element, visited: set[ET.Element]) -> bool:
            if elem in visited:
                return False
            visited.add(elem)
            tag = _strip_ns(elem.tag)
            if tag not in drawable:
                return False
            if tag == "use":
                ref = _use_href(elem)
                if not ref:
                    return False
                target = id_map.get(ref)
                if target is None:
                    return False
                return _is_drawable_target(target, visited)
            if tag == "g":
                for child in list(elem):
                    if _is_drawable_target(child, visited):
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

        def _is_drawable_element(elem: ET.Element) -> bool:
            if _is_in_defs(elem):
                return False
            tag = _strip_ns(elem.tag)
            if tag not in drawable:
                return False
            if tag == "use":
                ref = _use_href(elem)
                if not ref:
                    return False
                target = id_map.get(ref)
                if target is None:
                    return False
                return _is_drawable_target(target, set())
            if tag == "g":
                for child in list(elem):
                    if _is_drawable_element(child):
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

        for elem in root.iter():
            tag = _strip_ns(elem.tag)
            if tag == "defs":
                continue
            if tag in drawable and _is_drawable_element(elem):
                index = len(paths)
                paths.append(_path_to(elem))
                anim_map[index] = self._element_anim_types(elem)
        self._svg_root = root
        self._svg_paths = paths
        self._svg_anim_map = anim_map

    def _element_anim_types(self, elem: ET.Element) -> set[str]:
        types: set[str] = set()
        for child in list(elem):
            tag = child.tag.split("}", 1)[-1]
            if tag == "animateTransform":
                t = child.attrib.get("type")
                if t == "rotate":
                    types.add("rotate")
                elif t == "translate":
                    types.add("translate")
            elif tag == "animate":
                if child.attrib.get("attributeName") == "opacity":
                    types.add("opacity")
        return types

    def _render_svg_element(self, index: int, size_px: int) -> bytes | None:
        if self._svg_root is None or index >= len(self._svg_paths):
            return None
        root_copy = ET.fromstring(ET.tostring(self._svg_root))
        target_path = self._svg_paths[index]

        def _strip_ns(tag: str) -> str:
            return tag.split("}", 1)[1] if "}" in tag else tag

        def _filter(node: ET.Element, depth: int) -> None:
            for idx, child in list(enumerate(list(node))):
                tag = _strip_ns(child.tag)
                if tag == "defs":
                    continue
                if depth < len(target_path) and idx == target_path[depth]:
                    _filter(child, depth + 1)
                else:
                    node.remove(child)

        _filter(root_copy, 0)
        svg_bytes = ET.tostring(root_copy, encoding="utf-8")
        return _render_svg_bytes(svg_bytes, size_px)

    def _layer_index_map(self) -> dict[str, int]:
        if not self._svg_paths or not self._current_spec:
            return {}
        layers = self._spec_layers()
        if len(layers) != len(self._svg_paths):
            return {}
        return {layer["asset"]: idx for idx, layer in enumerate(layers)}

    def _update_dependencies(self) -> None:
        entries = [
            ("Pillow", "OK" if _ensure_pillow() else "missing"),
            ("cairosvg", "OK" if _has_cairosvg() else "missing"),
            ("rsvg-convert", "OK" if _has_rsvg() else "missing"),
        ]
        missing = [(name, status) for name, status in entries if status != "OK"]
        if not missing:
            self._deps_box.hide()
            return
        self._deps_box.show()
        text = " | ".join(f"{name}: {status}" for name, status in missing)
        self._deps_label.setText(text)

    @staticmethod
    def _clear_grid(layout: QtWidgets.QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _render_svg_png(svg_path: Path, size_px: int) -> bytes | None:
    png = _render_svg_with_cairosvg(svg_path.read_bytes(), size_px)
    if png is not None:
        return png
    return _render_svg_with_rsvg(svg_path.read_bytes(), size_px)

def _render_svg_bytes(svg_bytes: bytes, size_px: int) -> bytes | None:
    png = _render_svg_with_cairosvg(svg_bytes, size_px)
    if png is not None:
        return png
    return _render_svg_with_rsvg(svg_bytes, size_px)


def _render_svg_with_cairosvg(svg_bytes: bytes, size_px: int) -> bytes | None:
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=size_px, output_height=size_px)


def _render_svg_with_rsvg(svg_bytes: bytes, size_px: int) -> bytes | None:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            svg_path = Path(tmp_dir) / "preview.svg"
            output_path = Path(tmp_dir) / "preview.png"
            svg_path.write_bytes(svg_bytes)
            result = subprocess.run(
                [
                    "rsvg-convert",
                    "-w",
                    str(size_px),
                    "-h",
                    str(size_px),
                    "-o",
                    str(output_path),
                    str(svg_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None
            return output_path.read_bytes()
    except FileNotFoundError:
        return None


def _png_has_alpha(data: bytes) -> bool:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    if len(data) < 33:
        return False
    if data[12:16] != b"IHDR":
        return False
    color_type = data[25]
    return color_type in (4, 6)


def _ensure_pillow() -> bool:
    try:
        import PIL  # noqa: F401
    except Exception:
        return False
    return True


def _load_pil_image(data: bytes) -> "Image.Image" | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def _apply_transform(image: "Image.Image", rotation: float, opacity: float) -> "Image.Image":
    from PIL import Image

    out = image
    if rotation:
        out = out.rotate(-rotation, expand=True, resample=Image.BICUBIC)
    if opacity < 1.0:
        alpha = out.getchannel("A")
        alpha = alpha.point(lambda a: max(0, min(255, int(a * opacity))))
        out.putalpha(alpha)
    return out


def _apply_transform_with_pivot(
    image: "Image.Image", rotation: float, opacity: float, pivot_x: float, pivot_y: float
) -> tuple["Image.Image", tuple[float, float]]:
    from PIL import Image

    out = image
    if rotation:
        out = out.rotate(
            -rotation,
            expand=True,
            resample=Image.BICUBIC,
            center=(pivot_x, pivot_y),
        )
    if opacity < 1.0:
        alpha = out.getchannel("A")
        alpha = alpha.point(lambda a: max(0, min(255, int(a * opacity))))
        out.putalpha(alpha)

    if not rotation:
        return out, (pivot_x, pivot_y)

    rad = math.radians(rotation)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    corners = [
        (-pivot_x, -pivot_y),
        (image.width - pivot_x, -pivot_y),
        (-pivot_x, image.height - pivot_y),
        (image.width - pivot_x, image.height - pivot_y),
    ]
    rotated = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in corners]
    min_x = min(x for x, _ in rotated)
    min_y = min(y for _, y in rotated)
    pivot_offset = (pivot_x - min_x, pivot_y - min_y)
    return out, pivot_offset


def _has_cairosvg() -> bool:
    try:
        import cairosvg  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _has_rsvg() -> bool:
    return shutil.which("rsvg-convert") is not None


def main() -> int:
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS", "--disable-vulkan --disable-gpu"
    )
    os.environ.setdefault("QTWEBENGINE_DISABLE_GPU", "1")
    app = QtWidgets.QApplication([])
    window = WxSpecQtGui()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
