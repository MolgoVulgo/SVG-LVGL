import unittest

from pipeline.hash import fnv1a32
from pipeline.pack.toc import TOC_ENTRY_SIZE
from pipeline.spec.model import Asset, Components, LayerSpec, Metadata, Spec
from pipeline.wxpk import (
    HEADER_SIZE,
    MAGIC,
    WXPK_T_IMG,
    WXPK_T_JSON_SPEC,
    build_pack,
    extract_json_spec,
    parse_header,
    parse_toc,
)


class WxpkPackTests(unittest.TestCase):
    def _make_spec(self) -> Spec:
        layers = [
            LayerSpec(layer_id="sun", asset="sun", fx=["ROTATE"])
        ]
        fx = {"ROTATE": {"period_ms": 10000, "pivot_x": 0, "pivot_y": 0}}
        return Spec(
            spec_id=fnv1a32("clear_day"),
            name="clear_day",
            components=Components(
                decor="NONE",
                cover="NONE",
                particles="NONE",
                atmos="NONE",
                event="NONE",
            ),
            layers=layers,
            fx=fx,
            metadata=Metadata(version=1),
        )

    @staticmethod
    def _align_up(value: int, alignment: int = 4) -> int:
        return (value + alignment - 1) // alignment * alignment

    def test_build_pack_header_and_offsets(self) -> None:
        spec = self._make_spec()
        assets = [
            Asset(asset_key="sun", size_px=96, type="image", path="sun_96.bin"),
        ]
        payloads = {"sun": b"abcd"}
        pack = build_pack([spec], assets, payloads)

        header = parse_header(pack)
        self.assertEqual(header.magic, MAGIC)
        self.assertEqual(header.toc_count, 2)
        self.assertEqual(header.toc_offset, HEADER_SIZE)
        expected_blobs_offset = self._align_up(
            HEADER_SIZE + header.toc_count * TOC_ENTRY_SIZE
        )
        self.assertEqual(header.blobs_offset, expected_blobs_offset)

        toc_entries = parse_toc(pack, header)
        self.assertEqual(len(toc_entries), 2)
        asset_entry = toc_entries[0]
        json_entry = toc_entries[1]
        self.assertEqual(asset_entry.type_code, WXPK_T_IMG)
        self.assertEqual(asset_entry.offset, expected_blobs_offset)
        self.assertEqual(asset_entry.length, len(payloads["sun"]))
        expected_json_offset = self._align_up(asset_entry.offset + asset_entry.length)
        self.assertEqual(json_entry.type_code, WXPK_T_JSON_SPEC)
        self.assertEqual(json_entry.offset, expected_json_offset)

    def test_extract_json(self) -> None:
        spec = self._make_spec()
        assets = [
            Asset(asset_key="sun", size_px=96, type="image", path="sun_96.bin"),
        ]
        payloads = {"sun": b"data"}
        pack = build_pack([spec], assets, payloads)

        json_data = extract_json_spec(pack, spec.spec_id)
        self.assertEqual(json_data["name"], "clear_day")
        self.assertEqual(json_data["spec_id"], fnv1a32("clear_day"))
        self.assertEqual(json_data["metadata"]["version"], 1)

    def test_multi_asset_offsets(self) -> None:
        assets = [
            Asset(asset_key="sun", size_px=96, type="image", path="sun_96.bin"),
            Asset(asset_key="cloud", size_px=96, type="image", path="cloud_96.bin"),
        ]
        layers = [
            LayerSpec(layer_id="sun", asset="sun", fx=[]),
            LayerSpec(layer_id="cloud", asset="cloud", fx=[]),
        ]
        fx = {}
        spec = Spec(
            spec_id=fnv1a32("cloudy"),
            name="cloudy",
            components=Components(
                decor="NONE",
                cover="NONE",
                particles="NONE",
                atmos="NONE",
                event="NONE",
            ),
            layers=layers,
            fx=fx,
            metadata=Metadata(version=1),
        )

        payloads = {"sun": b"a", "cloud": b"bc"}
        pack = build_pack([spec], assets, payloads)
        header = parse_header(pack)
        toc_entries = parse_toc(pack, header)

        self.assertEqual(len(toc_entries), 3)
        first = toc_entries[0]
        second = toc_entries[1]
        json_entry = toc_entries[2]
        expected_first_offset = self._align_up(
            HEADER_SIZE + len(toc_entries) * TOC_ENTRY_SIZE
        )
        self.assertEqual(first.offset, expected_first_offset)
        self.assertEqual(second.offset, self._align_up(first.offset + first.length))
        expected_json_offset = self._align_up(second.offset + second.length)
        self.assertEqual(json_entry.offset, expected_json_offset)


if __name__ == "__main__":
    unittest.main()
