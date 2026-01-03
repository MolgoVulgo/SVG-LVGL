"""Desktop GUI for inspecting/editing wx.spec v1 JSON."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import base64
import io
import math
import random
import shutil
import subprocess
import tempfile
import time

from pipeline.mapping import map_svg_to_spec
from pipeline.wxspec import dumps_spec, parse_spec_dict
_CANVAS_SIZE = 320
_LAYER_COLORS = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)


class WxSpecGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WX Spec Inspector")
        self.geometry("980x640")
        self.minsize(860, 520)

        self._current_path: Path | None = None
        self._current_spec: dict | None = None
        self._current_svg: Path | None = None
        self._preview_image: tk.PhotoImage | None = None
        self._asset_images: dict[str, tk.PhotoImage] = {}
        self._asset_bitmaps: dict[str, "Image.Image"] = {}
        self._layer_images: list[tk.PhotoImage] = []
        self._no_renderer_warned = False
        self._svg_raster_cache: dict[int, bytes] = {}
        self._animation_job: str | None = None
        self._last_frame_time = 0.0
        self._start_time = time.time()
        self._active_tab = "svg"

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = tk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="Open SVG", command=self._open_svg).pack(
            side=tk.LEFT, padx=4
        )
        tk.Button(toolbar, text="Save", command=self._save).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Save As", command=self._save_as).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Refresh Preview", command=self._refresh).pack(
            side=tk.LEFT, padx=4
        )

        main = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main)
        right = tk.Frame(main)
        main.add(left, minsize=420)
        main.add(right, minsize=360)

        self._text = scrolledtext.ScrolledText(left, wrap=tk.NONE)
        self._text.pack(fill=tk.BOTH, expand=True)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=2)
        right.grid_rowconfigure(1, weight=0)
        right.grid_rowconfigure(2, weight=1)

        preview_frame = tk.LabelFrame(right, text="Preview")
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self._notebook = ttk.Notebook(preview_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._svg_tab = tk.Frame(self._notebook)
        self._assets_tab = tk.Frame(self._notebook)
        self._final_tab = tk.Frame(self._notebook)
        self._notebook.add(self._svg_tab, text="SVG")
        self._notebook.add(self._assets_tab, text="Assets")
        self._notebook.add(self._final_tab, text="Final")

        self._svg_canvas = tk.Canvas(
            self._svg_tab, width=_CANVAS_SIZE, height=_CANVAS_SIZE
        )
        self._svg_canvas.pack(padx=8, pady=8)

        self._assets_canvas = tk.Canvas(
            self._assets_tab, width=_CANVAS_SIZE, height=_CANVAS_SIZE
        )
        self._assets_canvas.pack(padx=8, pady=8)

        self._final_canvas = tk.Canvas(
            self._final_tab, width=_CANVAS_SIZE, height=_CANVAS_SIZE
        )
        self._final_canvas.pack(padx=8, pady=8)

        deps_frame = tk.LabelFrame(right, text="Dependencies")
        deps_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        self._deps_text = tk.Text(deps_frame, height=4, wrap=tk.NONE, state=tk.DISABLED)
        self._deps_text.pack(fill=tk.X, expand=False, padx=8, pady=6)
        self._update_dependencies()

        fx_frame = tk.LabelFrame(right, text="FX Enabled")
        fx_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self._fx_list = tk.Listbox(fx_frame)
        self._fx_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._status = tk.Label(self, text="Ready", anchor=tk.W)
        self._status.pack(side=tk.BOTTOM, fill=tk.X)

    def _set_status(self, text: str) -> None:
        self._status.config(text=text)

    def _update_dependencies(self) -> None:
        entries = []
        entries.append(("Pillow", "OK" if _ensure_pillow() else "missing"))
        entries.append(("cairosvg", "OK" if _has_cairosvg() else "missing"))
        entries.append(("rsvg-convert", "OK" if _has_rsvg() else "missing"))
        lines = [f"{name}: {status}" for name, status in entries]
        self._deps_text.configure(state=tk.NORMAL)
        self._deps_text.delete("1.0", tk.END)
        self._deps_text.insert(tk.END, "\n".join(lines))
        self._deps_text.configure(state=tk.DISABLED)

    def _on_tab_changed(self, _: object) -> None:
        current = self._notebook.tab(self._notebook.select(), "text").lower()
        self._active_tab = current
        self._refresh()

    def _open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open wx.spec v1 JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._current_path = Path(path)
        self._current_svg = None
        self._svg_raster_cache.clear()
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, self._current_path.read_text(encoding="utf-8"))
        self._refresh()

    def _open_svg(self) -> None:
        path = filedialog.askopenfilename(
            title="Open SVG",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
        )
        if not path:
            return
        svg_path = Path(path)
        try:
            spec = map_svg_to_spec(svg_path)
            serialized = dumps_spec(spec, indent=2)
            self._text.delete("1.0", tk.END)
            self._text.insert(tk.END, serialized)
            self._current_path = None
            self._current_svg = svg_path
            self._svg_raster_cache.clear()
            self._refresh()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("SVG conversion failed", str(exc))

    def _save(self) -> None:
        if self._current_path is None:
            self._save_as()
            return
        self._write_to_path(self._current_path)

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save wx.spec v1 JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._current_path = Path(path)
        self._write_to_path(self._current_path)

    def _write_to_path(self, path: Path) -> None:
        try:
            data = self._parse_text()
            spec = parse_spec_dict(data)
            serialized = dumps_spec(spec, indent=2)
            path.write_text(serialized, encoding="utf-8")
            self._text.delete("1.0", tk.END)
            self._text.insert(tk.END, serialized)
            self._set_status(f"Saved {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Save failed", str(exc))

    def _parse_text(self) -> dict:
        raw = self._text.get("1.0", tk.END).strip()
        if not raw:
            raise ValueError("JSON text is empty")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("root JSON must be an object")
        return data

    def _refresh(self) -> None:
        try:
            data = self._parse_text()
            spec = parse_spec_dict(data)
            self._current_spec = spec.to_dict()
            self._render()
            self._set_status("Preview updated")
        except Exception as exc:  # noqa: BLE001
            self._current_spec = None
            self._clear_previews()
            self._fx_list.delete(0, tk.END)
            self._set_status(f"Error: {exc}")

    def _render(self) -> None:
        self._clear_previews()
        self._fx_list.delete(0, tk.END)
        self._asset_images = {}
        self._asset_bitmaps = {}
        self._layer_images = []
        if not self._current_spec:
            return

        size_px = int(self._current_spec.get("size_px", 64))
        if size_px <= 0:
            return
        scale = _CANVAS_SIZE / size_px

        self._draw_frame(self._active_canvas())

        self._preview_image = None
        if self._active_tab != "final":
            self._stop_animation()
        if self._active_tab == "svg":
            self._render_svg_tab()
        elif self._active_tab == "assets":
            self._render_assets_preview(scale)
        elif self._active_tab == "final":
            self._render_final_preview(scale)

        if self._active_tab != "final":
            layers = sorted(self._current_spec.get("layers", []), key=lambda x: x["z"])
            for index, layer in enumerate(layers):
                x = int(layer["x"] * scale)
                y = int(layer["y"] * scale)
                w = int(layer["w"] * scale)
                h = int(layer["h"] * scale)
                color = _LAYER_COLORS[index % len(_LAYER_COLORS)]
                canvas = self._active_canvas()
                canvas.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + h,
                    outline=color,
                    width=2,
                )
                canvas.create_text(
                    x + w / 2,
                    y + h / 2,
                    text=layer["asset_key"],
                    fill=color,
                    font=("Arial", 8),
                )

        fx = self._current_spec.get("fx", {})
        for key, value in fx.items():
            if isinstance(value, dict) and value.get("enabled"):
                self._fx_list.insert(tk.END, f"{key} -> z={value.get('target_z')}")

    def _render_svg_tab(self) -> None:
        self._render_svg_preview()

    def _render_svg_preview(self) -> None:
        if not self._current_svg or not hasattr(self, "_svg_canvas"):
            return
        png_bytes = self._get_svg_raster(_CANVAS_SIZE)
        if png_bytes is None:
            self._set_status("Preview: SVG renderer not available")
            if not self._no_renderer_warned:
                messagebox.showerror(
                    "Preview unavailable",
                    "No SVG renderer found. Install cairosvg or rsvg-convert.",
                )
                self._no_renderer_warned = True
            return
        b64 = base64.b64encode(png_bytes).decode("ascii")
        self._preview_image = tk.PhotoImage(data=b64)
        self._svg_canvas.create_image(
            _CANVAS_SIZE // 2,
            _CANVAS_SIZE // 2,
            image=self._preview_image,
        )

    def _render_assets_preview(self, scale: float) -> None:
        assets = self._current_spec.get("assets", [])
        if not assets:
            return
        assets_root = self._resolve_assets_root()
        tile = int(max(1, _CANVAS_SIZE // max(1, len(assets))))
        x = 0
        y = 0
        placed = 0
        for asset in assets:
            asset_key = asset["asset_key"]
            asset_path = self._asset_path(assets_root, asset)
            image = self._load_asset_image(assets_root, asset)
            if image is None and asset_path.exists():
                if not _png_has_alpha(asset_path.read_bytes()):
                    self._set_status(f"Asset {asset_key} is not PNG+alpha")
                    continue
            if image is None:
                image = self._load_svg_fallback_image(asset)
            if image is None:
                continue
            self._asset_images[asset_key] = image
            self._assets_canvas.create_image(x + tile // 2, y + tile // 2, image=image)
            self._assets_canvas.create_text(
                x + tile // 2,
                y + tile - 10,
                text=asset_key,
                fill="#555",
                font=("Arial", 8),
            )
            x += tile
            if x + tile > _CANVAS_SIZE:
                x = 0
                y += tile
            placed += 1
        if placed == 0:
            self._assets_canvas.create_text(
                _CANVAS_SIZE // 2,
                _CANVAS_SIZE // 2,
                text="No PNG+alpha assets found.",
                fill="#777",
                font=("Arial", 10),
            )

    def _render_final_preview(self, scale: float) -> None:
        if not _ensure_pillow():
            messagebox.showerror(
                "Preview unavailable",
                "Final preview requires Pillow (PIL). Install it to enable FX simulation.",
            )
            return
        self._prepare_asset_bitmaps()
        if not self._asset_bitmaps:
            self._final_canvas.create_text(
                _CANVAS_SIZE // 2,
                _CANVAS_SIZE // 2,
                text="No PNG+alpha assets found.",
                fill="#777",
                font=("Arial", 10),
            )
            return
        self._start_animation(scale)

    def _draw_frame(self, canvas: tk.Canvas) -> None:
        canvas.create_rectangle(
            1, 1, _CANVAS_SIZE - 1, _CANVAS_SIZE - 1, outline="#444"
        )

    def _clear_previews(self) -> None:
        if hasattr(self, "_svg_canvas"):
            self._svg_canvas.delete("all")
        self._assets_canvas.delete("all")
        self._final_canvas.delete("all")

    def _active_canvas(self) -> tk.Canvas:
        if self._active_tab == "assets":
            return self._assets_canvas
        if self._active_tab == "final":
            return self._final_canvas
        return self._svg_canvas

    def _resolve_assets_root(self) -> Path:
        if self._current_path is not None:
            return self._current_path.parent
        if self._current_svg is not None:
            return self._current_svg.parent
        return Path.cwd()

    def _load_asset_image(self, root: Path, asset: dict) -> tk.PhotoImage | None:
        path = root / asset.get("path", "")
        if not path.exists():
            return None
        data = path.read_bytes()
        if not _png_has_alpha(data):
            return None
        b64 = base64.b64encode(data).decode("ascii")
        try:
            return tk.PhotoImage(data=b64)
        except tk.TclError:
            return None

    def _prepare_asset_bitmaps(self) -> None:
        assets_root = self._resolve_assets_root()
        assets = self._current_spec.get("assets", [])
        for asset in assets:
            asset_key = asset["asset_key"]
            if asset_key in self._asset_bitmaps:
                continue
            path = self._asset_path(assets_root, asset)
            if not path.exists():
                image = self._load_svg_fallback_bitmap(asset)
                if image is not None:
                    self._asset_bitmaps[asset_key] = image
                continue
            data = path.read_bytes()
            if not _png_has_alpha(data):
                self._set_status(f"Asset {asset_key} is not PNG+alpha")
                continue
            image = _load_pil_image(data)
            if image is None:
                continue
            self._asset_bitmaps[asset_key] = image

    def _get_svg_raster(self, size_px: int) -> bytes | None:
        if not self._current_svg:
            return None
        cached = self._svg_raster_cache.get(size_px)
        if cached:
            return cached
        png_bytes = _render_svg_png(self._current_svg, size_px)
        if png_bytes is None:
            return None
        self._svg_raster_cache[size_px] = png_bytes
        return png_bytes

    def _load_svg_fallback_image(self, asset: dict) -> tk.PhotoImage | None:
        size_px = int(asset.get("size_px", 0)) or _CANVAS_SIZE
        png_bytes = self._get_svg_raster(size_px)
        if png_bytes is None:
            return None
        b64 = base64.b64encode(png_bytes).decode("ascii")
        try:
            return tk.PhotoImage(data=b64)
        except tk.TclError:
            return None

    def _load_svg_fallback_bitmap(self, asset: dict) -> "Image.Image" | None:
        size_px = int(asset.get("size_px", 0)) or _CANVAS_SIZE
        png_bytes = self._get_svg_raster(size_px)
        if png_bytes is None:
            return None
        return _load_pil_image(png_bytes)

    def _asset_path(self, root: Path, asset: dict) -> Path:
        return root / asset.get("path", "")

    def _start_animation(self, scale: float) -> None:
        self._stop_animation()
        now = time.time()
        self._start_time = now
        self._last_frame_time = now
        self._animation_job = self.after(0, lambda: self._animate_frame(scale))

    def _stop_animation(self) -> None:
        if self._animation_job is not None:
            self.after_cancel(self._animation_job)
            self._animation_job = None

    def _animate_frame(self, scale: float) -> None:
        if not self._current_spec:
            return
        now = time.time()
        dt = now - self._last_frame_time
        self._last_frame_time = now
        elapsed = now - self._start_time

        self._final_canvas.delete("preview")
        self._layer_images = []

        layers = sorted(self._current_spec.get("layers", []), key=lambda x: x["z"])
        assets = {asset["asset_key"]: asset for asset in self._current_spec.get("assets", [])}
        fx = self._current_spec.get("fx", {})

        for layer in layers:
            asset = assets.get(layer["asset_key"])
            if not asset:
                continue
            base = self._asset_bitmaps.get(layer["asset_key"])
            if base is None:
                continue
            img = base
            offset_x = 0.0
            offset_y = 0.0
            opacity = 1.0
            rotation = 0.0

            for key, value in fx.items():
                if not isinstance(value, dict) or not value.get("enabled"):
                    continue
                if int(value.get("target_z", -1)) != int(layer["z"]):
                    continue
                if key == "ROTATE":
                    speed = float(value.get("speed_dps", 0))
                    rotation = (elapsed * speed) % 360.0
                elif key == "FALL":
                    speed = float(value.get("speed_pps", 0))
                    offset_y = (elapsed * speed) % layer["h"]
                elif key == "FLOW_X":
                    speed = float(value.get("speed_pps", 0))
                    rng = float(value.get("range_px", layer["w"]))
                    if rng <= 0:
                        rng = layer["w"]
                    offset_x = (elapsed * speed) % rng
                elif key == "JITTER":
                    amp = float(value.get("amp_px", 0))
                    offset_x += random.uniform(-amp, amp)
                    offset_y += random.uniform(-amp, amp)
                elif key == "DRIFT":
                    amp = float(value.get("amp_px", 0))
                    speed = float(value.get("speed_pps", 0))
                    offset_x += math.sin(elapsed * speed * 0.01) * amp
                    offset_y += math.cos(elapsed * speed * 0.01) * amp
                elif key == "TWINKLE":
                    period = float(value.get("period_ms", 0)) / 1000.0
                    if period > 0:
                        opacity *= 0.5 + 0.5 * math.sin(elapsed * 2 * math.pi / period)
                elif key == "FLASH":
                    period = float(value.get("period_ms", 0)) / 1000.0
                    if period > 0:
                        opacity *= 1.0 if (elapsed % period) < (period / 2) else 0.0
                elif key == "CROSSFADE":
                    period = float(value.get("period_ms", 0)) / 1000.0
                    if period > 0:
                        opacity *= 0.5 + 0.5 * math.cos(elapsed * 2 * math.pi / period)

            img = _apply_transform(img, rotation, opacity)
            tk_img = _pil_to_tk(img, scale)
            self._layer_images.append(tk_img)

            x = int((layer["x"] + offset_x) * scale)
            y = int((layer["y"] + offset_y) * scale)
            self._final_canvas.create_image(
                x, y, image=tk_img, anchor=tk.NW, tags="preview"
            )

        self._animation_job = self.after(33, lambda: self._animate_frame(scale))


def _render_svg_png(svg_path: Path, size_px: int) -> bytes | None:
    png = _render_svg_with_cairosvg(svg_path, size_px)
    if png is not None:
        return png
    return _render_svg_with_rsvg(svg_path, size_px)


def _render_svg_with_cairosvg(svg_path: Path, size_px: int) -> bytes | None:
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None
    svg_bytes = svg_path.read_bytes()
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=size_px, output_height=size_px)


def _render_svg_with_rsvg(svg_path: Path, size_px: int) -> bytes | None:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "preview.png"
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


def _has_cairosvg() -> bool:
    try:
        import cairosvg  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _has_rsvg() -> bool:
    return shutil.which("rsvg-convert") is not None


def _scale_image(image: tk.PhotoImage, scale: float) -> tk.PhotoImage:
    if scale <= 0:
        return image
    if abs(scale - 1.0) < 0.01:
        return image
    if abs(scale - round(scale)) < 0.01:
        factor = int(round(scale))
        return image.zoom(factor, factor)
    return image


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


def _pil_to_tk(image: "Image.Image", scale: float) -> tk.PhotoImage:
    from PIL import ImageTk

    out = image
    if abs(scale - 1.0) > 0.01:
        w = max(1, int(out.width * scale))
        h = max(1, int(out.height * scale))
        out = out.resize((w, h), resample=Image.BICUBIC)
    return ImageTk.PhotoImage(out)


def main() -> int:
    app = WxSpecGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
