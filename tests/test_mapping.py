import tempfile
import unittest
from pathlib import Path

from pipeline.hash import fnv1a32
from pipeline.mapping import map_svg_to_spec


class MappingTests(unittest.TestCase):
    def _write_svg(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
        handle.write(content.encode("utf-8"))
        handle.close()
        return Path(handle.name)

    def test_minimal_svg_mapping(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="clear_day" data-wx-fx-ROTATE='{"period_ms": 10000, "pivot_x": 0, "pivot_y": 0, "target_z": 10}' xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="10"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(spec.name, "clear_day")
        self.assertEqual(spec.spec_id, fnv1a32("clear_day"))
        self.assertEqual(len(spec.layers), 1)
        self.assertEqual(spec.layers[0].asset, "sun")
        self.assertIn("ROTATE", spec.layers[0].fx)

    def test_missing_layers(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="empty" xmlns="http://www.w3.org/2000/svg"></svg>"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(len(spec.layers), 1)
        self.assertEqual(spec.layers[0].asset, "empty")

    def test_invalid_z_value(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="bad_z" xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="bad"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            with self.assertRaises(ValueError):
                map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_size(self) -> None:
        svg = """<svg data-wx-id="no_size" xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="10"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            with self.assertRaises(ValueError):
                map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)

    def test_invalid_fx_json(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="bad_fx" data-wx-fx-ROTATE='{"enabled": true' xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="10"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            with self.assertRaises(ValueError):
                map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)

    def test_fallback_spec_id(self) -> None:
        svg = """<svg width="96" height="96" xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="10"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertTrue(spec.name)

    def test_auto_fx_from_animations(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="auto_fx" xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="0">
    <animateTransform attributeName="transform" type="rotate" values="0 0 0; 360 0 0" dur="10s" repeatCount="indefinite"/>
  </g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertIn("ROTATE", spec.fx)
        self.assertEqual(spec.fx["ROTATE"]["period_ms"], 10000)
        self.assertIn("ROTATE", spec.layers[0].fx)

    def test_gradient_clone_reuse(self) -> None:
        svg = """<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <linearGradient id="c" x1="0" y1="0" x2="1" y2="1" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#4286ee"/>
      <stop offset="1" stop-color="#0950bc"/>
    </linearGradient>
    <linearGradient id="d" x1="0" y1="0" x2="1" y2="1" xlink:href="#c"/>
    <linearGradient id="e" x1="0" y1="0" x2="1" y2="1" xlink:href="#c"/>
  </defs>
  <line x1="0" y1="0" x2="0" y2="10" stroke="url(#c)" stroke-width="2"/>
  <line x1="10" y1="0" x2="10" y2="10" stroke="url(#d)" stroke-width="2"/>
  <line x1="20" y1="0" x2="20" y2="10" stroke="url(#e)" stroke-width="2"/>
</svg>
"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(len(spec.layers), 3)
        self.assertEqual(spec.layers[1].asset, spec.layers[0].asset)
        self.assertEqual(spec.layers[2].asset, spec.layers[0].asset)


if __name__ == "__main__":
    unittest.main()
