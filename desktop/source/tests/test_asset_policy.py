import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lertx.assets import require_local_path, preflight_layers
from lertx.document import SceneDocument


class AssetPolicyTests(unittest.TestCase):
    def test_resolver_and_network_schemes_rejected(self):
        for value in ("https://example.invalid/a.usd", "omniverse://host/scene.usd",
                      "custom:asset", "//host/share/file.usd", "\\\\host\\share\\file.usd"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_local_path(value)

    def test_nested_remote_texture_rejected_before_stage_open(self):
        from pxr import Sdf, Usd
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = Sdf.Layer.CreateNew(str(root/"nested.usda"))
            prim = Sdf.CreatePrimInLayer(nested, "/Shader")
            attribute = Sdf.AttributeSpec(prim, "texture", Sdf.ValueTypeNames.Asset)
            attribute.default = Sdf.AssetPath("https://example.invalid/texture.png")
            nested.Save()
            layer = Sdf.Layer.CreateNew(str(root/"scene.usda"))
            layer.subLayerPaths = ["nested.usda"]
            layer.Save()
            with patch.object(Usd.Stage, "Open") as opened:
                with self.assertRaisesRegex(ValueError, "Remote"):
                    SceneDocument(root/"scene.usda")
                opened.assert_not_called()

    def test_dependency_cycle_is_bounded(self):
        from pxr import Sdf
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = Sdf.Layer.CreateNew(str(root/"a.usda"))
            b = Sdf.Layer.CreateNew(str(root/"b.usda"))
            a.subLayerPaths = ["b.usda"]
            b.subLayerPaths = ["a.usda"]
            a.Save()
            b.Save()
            self.assertEqual(preflight_layers(root/"a.usda"), 2)
            with self.assertRaisesRegex(ValueError, "limit"):
                preflight_layers(root/"a.usda", max_layers=1)
