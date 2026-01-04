import unittest

from pipeline.hash import fnv1a32
from pipeline.spec.model import Components, LayerSpec, Metadata, Spec
from pipeline.wxspec import validate_spec


class ValidationTests(unittest.TestCase):
    def _base_spec(self) -> Spec:
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

    def test_fx_missing_field(self) -> None:
        spec = self._base_spec()
        spec.fx["ROTATE"] = {"unknown": 1}
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_layer_duplicate_id(self) -> None:
        spec = self._base_spec()
        spec.layers.append(
            LayerSpec(layer_id="sun", asset="sun", fx=[])
        )
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_fx_missing_for_layer(self) -> None:
        spec = self._base_spec()
        spec.layers[0].fx = ["FLASH"]
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_fx_negative_values(self) -> None:
        spec = self._base_spec()
        spec.fx["FLOW_X"] = {"period_ms": -1, "amp_x": -5}
        with self.assertRaises(ValueError):
            validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
