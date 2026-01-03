import tempfile
import unittest
from pathlib import Path

from pipeline.mapping import map_svg_to_spec


class MappingTests(unittest.TestCase):
    def _write_svg(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
        handle.write(content.encode("utf-8"))
        handle.close()
        return Path(handle.name)

    def test_minimal_svg_mapping(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="clear_day" data-wx-fx-ROTATE='{"enabled": true, "target_z": 10, "speed_dps": 12}' xmlns="http://www.w3.org/2000/svg">
  <g data-wx-asset="sun" data-wx-z="10"></g>
</svg>
"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(spec.id, "clear_day")
        self.assertEqual(spec.size_px, 96)
        self.assertEqual(len(spec.assets), 1)
        self.assertEqual(spec.assets[0].asset_key, "sun")
        self.assertEqual(len(spec.layers), 1)
        self.assertEqual(spec.layers[0].z, 10)

    def test_missing_layers(self) -> None:
        svg = """<svg width="96" height="96" data-wx-id="empty" xmlns="http://www.w3.org/2000/svg"></svg>"""
        path = self._write_svg(svg)
        try:
            spec = map_svg_to_spec(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(len(spec.layers), 1)
        self.assertEqual(spec.layers[0].asset_key, "empty")

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
        self.assertTrue(spec.id)

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
        self.assertTrue(spec.fx["ROTATE"]["enabled"])
        self.assertEqual(spec.fx["ROTATE"]["target_z"], 0)


if __name__ == "__main__":
    unittest.main()
