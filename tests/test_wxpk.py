import unittest

from pipeline.spec.model import Asset, Layer, Spec
from pipeline.wxspec import ensure_fx_complete
from pipeline.pack.toc import TOC_ENTRY_SIZE
from pipeline.wxpk import HEADER_SIZE, MAGIC, build_pack, extract_json, parse_header, parse_toc


class WxpkPackTests(unittest.TestCase):
    def _make_spec(self) -> Spec:
        assets = [
            Asset(asset_key="sun", size_px=96, type="image", path="sun_96.bin"),
        ]
        layers = [
            Layer(
                z=10,
                asset_key="sun",
                x=0,
                y=0,
                w=96,
                h=96,
                pivot_x=48,
                pivot_y=48,
                opacity=255,
            )
        ]
        fx = ensure_fx_complete()
        fx["ROTATE"].enabled = True
        fx["ROTATE"].target_z = 10
        fx["ROTATE"].speed_dps = 12
        return Spec(id="clear_day", size_px=96, assets=assets, layers=layers, fx=fx)

    def test_build_pack_header_and_offsets(self) -> None:
        spec = self._make_spec()
        payloads = {"sun": b"abcd"}
        pack = build_pack(spec, payloads)

        header = parse_header(pack)
        self.assertEqual(header.magic, MAGIC)
        self.assertEqual(header.toc_count, 1)
        self.assertEqual(header.toc_offset, HEADER_SIZE)

        toc_entries = parse_toc(pack, header)
        self.assertEqual(len(toc_entries), 1)
        entry = toc_entries[0]
        expected_payload_offset = HEADER_SIZE + TOC_ENTRY_SIZE
        self.assertEqual(entry.payload_offset, expected_payload_offset)
        self.assertEqual(entry.payload_size, len(payloads["sun"]))

        expected_json_offset = expected_payload_offset + len(payloads["sun"])
        self.assertEqual(header.json_offset, expected_json_offset)
        self.assertEqual(header.pack_size, len(pack))

    def test_extract_json(self) -> None:
        spec = self._make_spec()
        payloads = {"sun": b"data"}
        pack = build_pack(spec, payloads)

        json_data = extract_json(pack)
        self.assertEqual(json_data["id"], "clear_day")
        self.assertEqual(json_data["size_px"], 96)
        self.assertEqual(json_data["version"], "wx.spec.v1")

    def test_multi_asset_offsets(self) -> None:
        assets = [
            Asset(asset_key="sun", size_px=96, type="image", path="sun_96.bin"),
            Asset(asset_key="cloud", size_px=96, type="image", path="cloud_96.bin"),
        ]
        layers = [
            Layer(
                z=10,
                asset_key="sun",
                x=0,
                y=0,
                w=96,
                h=96,
                pivot_x=48,
                pivot_y=48,
                opacity=255,
            ),
            Layer(
                z=20,
                asset_key="cloud",
                x=0,
                y=0,
                w=96,
                h=96,
                pivot_x=48,
                pivot_y=48,
                opacity=255,
            ),
        ]
        fx = ensure_fx_complete()
        fx["ROTATE"].enabled = True
        fx["ROTATE"].target_z = 10
        fx["ROTATE"].speed_dps = 12
        spec = Spec(id="cloudy", size_px=96, assets=assets, layers=layers, fx=fx)

        payloads = {"sun": b"a", "cloud": b"bc"}
        pack = build_pack(spec, payloads)
        header = parse_header(pack)
        toc_entries = parse_toc(pack, header)

        self.assertEqual(len(toc_entries), 2)
        first = toc_entries[0]
        second = toc_entries[1]
        self.assertEqual(first.payload_offset, HEADER_SIZE + 2 * TOC_ENTRY_SIZE)
        self.assertEqual(second.payload_offset, first.payload_offset + first.payload_size)
        expected_json_offset = second.payload_offset + second.payload_size
        self.assertEqual(header.json_offset, expected_json_offset)


if __name__ == "__main__":
    unittest.main()
