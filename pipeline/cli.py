"""CLI entry points for the WX pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.mapping import map_svg_to_spec
from pipeline.wxpk import build_pack_from_files
from pipeline.wxspec import dumps_spec
from pipeline.wxspec import parse_spec_dict


def _load_spec(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _cmd_pack(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    if not spec_path.exists():
        raise FileNotFoundError(f"spec not found: {spec_path}")

    assets_root = Path(args.assets_root) if args.assets_root else spec_path.parent
    spec_dict = _load_spec(spec_path)
    spec = parse_spec_dict(spec_dict)

    pack = build_pack_from_files(spec, assets_root)
    output_path = Path(args.output)
    output_path.write_bytes(pack)
    return 0


def _cmd_map(args: argparse.Namespace) -> int:
    svg_path = Path(args.svg)
    if not svg_path.exists():
        raise FileNotFoundError(f"svg not found: {svg_path}")

    spec = map_svg_to_spec(
        svg_path,
        spec_id=args.spec_id,
        size_px=args.size_px,
    )
    output_path = Path(args.output)
    output_path.write_text(dumps_spec(spec, indent=2), encoding="utf-8")
    return 0


def _cmd_map_pack(args: argparse.Namespace) -> int:
    svg_path = Path(args.svg)
    if not svg_path.exists():
        raise FileNotFoundError(f"svg not found: {svg_path}")

    spec = map_svg_to_spec(
        svg_path,
        spec_id=args.spec_id,
        size_px=args.size_px,
    )

    assets_root = Path(args.assets_root) if args.assets_root else svg_path.parent
    pack = build_pack_from_files(spec, assets_root)
    output_path = Path(args.output)
    output_path.write_bytes(pack)
    return 0


def _cmd_gui_qt(_: argparse.Namespace) -> int:
    from pipeline.gui_qt import main as gui_main

    return gui_main()


def main() -> int:
    parser = argparse.ArgumentParser(prog="wx-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack_parser = subparsers.add_parser("pack", help="Build WXPK v1 from JSON spec")
    pack_parser.add_argument("--spec", required=True, help="Path to wx.spec v1 JSON")
    pack_parser.add_argument(
        "--assets-root",
        help="Root directory for asset payloads (defaults to spec directory)",
    )
    pack_parser.add_argument("--output", required=True, help="Output pack file")
    pack_parser.set_defaults(func=_cmd_pack)

    map_parser = subparsers.add_parser("map", help="Map SVG to wx.spec v1 JSON")
    map_parser.add_argument("--svg", required=True, help="Path to SVG input")
    map_parser.add_argument(
        "--spec-id",
        help="Spec id value (fallback to SVG data-wx-id or filename)",
    )
    map_parser.add_argument(
        "--size-px",
        type=int,
        help="Override size_px (defaults to SVG size)",
    )
    map_parser.add_argument("--output", required=True, help="Output JSON spec file")
    map_parser.set_defaults(func=_cmd_map)

    map_pack_parser = subparsers.add_parser(
        "map-pack", help="Map SVG to wx.spec and build WXPK v1"
    )
    map_pack_parser.add_argument("--svg", required=True, help="Path to SVG input")
    map_pack_parser.add_argument(
        "--spec-id",
        help="Spec id value (fallback to SVG data-wx-id or filename)",
    )
    map_pack_parser.add_argument(
        "--size-px",
        type=int,
        help="Override size_px (defaults to SVG size)",
    )
    map_pack_parser.add_argument(
        "--assets-root",
        help="Root directory for asset payloads (defaults to SVG directory)",
    )
    map_pack_parser.add_argument("--output", required=True, help="Output pack file")
    map_pack_parser.set_defaults(func=_cmd_map_pack)

    gui_parser = subparsers.add_parser("gui", help="Open wx.spec GUI (Qt)")
    gui_parser.set_defaults(func=_cmd_gui_qt)

    gui_qt_parser = subparsers.add_parser("gui-qt", help="Open wx.spec GUI (Qt)")
    gui_qt_parser.set_defaults(func=_cmd_gui_qt)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
