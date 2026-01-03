import unittest

from pipeline.spec.model import Asset, Layer, Spec
from pipeline.wxspec import ensure_fx_complete, validate_spec


class ValidationTests(unittest.TestCase):
    def _base_spec(self) -> Spec:
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

    def test_fx_missing_field(self) -> None:
        spec = self._base_spec()
        spec.fx["ROTATE"] = {"enabled": True, "target_z": 10}
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_layer_pivot_out_of_bounds(self) -> None:
        spec = self._base_spec()
        spec.layers[0].pivot_x = 200
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_layer_duplicate_z(self) -> None:
        spec = self._base_spec()
        spec.layers.append(
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
        )
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_fx_target_z_missing(self) -> None:
        spec = self._base_spec()
        spec.fx["ROTATE"].target_z = 999
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_fx_negative_values(self) -> None:
        spec = self._base_spec()
        spec.fx["FLOW_X"] = {
            "enabled": True,
            "target_z": 10,
            "speed_pps": -1,
            "range_px": -5,
        }
        with self.assertRaises(ValueError):
            validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
