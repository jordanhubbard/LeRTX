"""Actual USD tests; missing USD is a failure, not a skip."""
import tempfile
import unittest
from pathlib import Path

from lertx.document import SceneDocument


class DocumentTests(unittest.TestCase):
    def test_configured_asset_search_path_resolves_missing_relative_asset(self):
        from pxr import Sdf
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root/"assets"
            assets.mkdir()
            child = Sdf.Layer.CreateNew(str(assets/"child.usda"))
            Sdf.CreatePrimInLayer(child, "/ResolvedChild")
            child.Save()
            layer = Sdf.Layer.CreateNew(str(root/"scene.usda"))
            layer.subLayerPaths = ["child.usda"]
            layer.Save()
            doc = SceneDocument(root/"scene.usda", [str(assets)])
            self.assertTrue(doc.stage.GetPrimAtPath("/ResolvedChild"))
            self.assertEqual(Path(doc.stage.GetRootLayer().subLayerPaths[0]), (assets/"child.usda").resolve())

    def test_relative_assets_survive_private_layer_and_save_as(self):
        from pxr import Usd, Sdf
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = Usd.Stage.CreateNew(str(root/"child.usda"))
            child.DefinePrim("/Child")
            child.GetRootLayer().Save()
            stage = Usd.Stage.CreateNew(str(root/"scene.usda"))
            stage.GetRootLayer().subLayerPaths = ["child.usda"]
            prim = stage.DefinePrim("/Asset")
            prim.CreateAttribute("texture", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("texture.png"))
            stage.GetRootLayer().Save()
            doc = SceneDocument(root/"scene.usda")
            self.assertTrue(doc.stage.GetPrimAtPath("/Child"))
            destination = root/"copy"
            destination.mkdir()
            doc.save(destination/"scene.usda")
            loaded = SceneDocument(destination/"scene.usda")
            self.assertTrue(loaded.stage.GetPrimAtPath("/Child"))
            self.assertEqual(Path(loaded.stage.GetPrimAtPath("/Asset").GetAttribute("texture").Get().path),
                             (root/"texture.png").resolve())

    def test_shear_is_rejected_without_mutating(self):
        from pxr import Usd, UsdGeom, Gf
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"shear.usda"
            stage = Usd.Stage.CreateNew(str(path))
            matrix = Gf.Matrix4d(1)
            matrix.SetRow(0, Gf.Vec4d(1, .4, 0, 0))
            UsdGeom.Xform.Define(stage, "/Shear").AddTransformOp().Set(matrix)
            stage.GetRootLayer().Save()
            doc = SceneDocument(path)
            with self.assertRaisesRegex(ValueError, "sheared"):
                doc.edit_transform("/Shear", [0]*3, [0]*3, [1]*3)
            self.assertFalse(doc.dirty)

    def test_documents_are_isolated_and_discard_reads_disk(self):
        from pxr import Usd, UsdGeom
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.usda"
            stage = Usd.Stage.CreateNew(str(path))
            UsdGeom.Cube.Define(stage, "/Box")
            stage.GetRootLayer().Save()
            first, second = SceneDocument(path), SceneDocument(path)
            first.edit_transform("/Box", [1, 2, 3], [20, 30, 40], [2, 3, 4])
            self.assertEqual(second.transform("/Box")["translation"], [0, 0, 0])
            self.assertEqual(SceneDocument(path).transform("/Box")["translation"], [0, 0, 0])
            before = UsdGeom.Xformable(first.stage.GetPrimAtPath("/Box")).GetLocalTransformation()
            values = first.transform("/Box")
            first.edit_transform("/Box", **values)
            after = UsdGeom.Xformable(first.stage.GetPrimAtPath("/Box")).GetLocalTransformation()
            for i in range(4):
                for j in range(4):
                    self.assertAlmostEqual(before[i][j], after[i][j], places=5)

    def test_edit_save_reopen_and_failed_save(self):
        from pxr import Usd, UsdGeom, Gf, Sdf

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.usda"
            stage = Usd.Stage.CreateNew(str(path))
            parent = UsdGeom.Xform.Define(stage, "/World")
            parent.AddTranslateOp().Set(Gf.Vec3d(10, 0, 0))
            UsdGeom.Cube.Define(stage, "/World/Box")
            stage.GetRootLayer().Save()
            before = path.read_bytes()
            doc = SceneDocument(path)
            doc.edit_transform("/World/Box", [1, 2, 3], [0, 0, 0], [2, 3, 4])
            self.assertTrue(doc.dirty)
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(OSError):
                doc.save(Path(directory) / "missing" / "scene.usda")
            self.assertTrue(doc.dirty)
            doc.save()
            self.assertFalse(doc.dirty)
            self.assertNotEqual(path.read_bytes(), before)
            # Bypass USD's layer registry: prove persisted bytes, not cached edits.
            disk = Usd.Stage.Open(Sdf.Layer.OpenAsAnonymous(str(path)))
            disk_box = UsdGeom.Xformable(disk.GetPrimAtPath("/World/Box"))
            self.assertEqual(list(disk_box.GetLocalTransformation().ExtractTranslation()), [1, 2, 3])
            reopened = SceneDocument(path)
            self.assertEqual(reopened.transform("/World/Box")["translation"], [1, 2, 3])
            world = UsdGeom.Xformable(reopened.stage.GetPrimAtPath("/World/Box"))
            self.assertEqual(list(world.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()), [11, 2, 3])
            saved_as = Path(directory) / "copy.usdc"
            doc.save(saved_as)
            self.assertEqual(SceneDocument(saved_as).transform("/World/Box")["scale"], [2, 3, 4])

    def test_invalid_edit_does_not_mutate(self):
        from pxr import Usd, UsdGeom
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.usda"
            stage = Usd.Stage.CreateNew(str(path))
            UsdGeom.Cube.Define(stage, "/Box")
            stage.GetRootLayer().Save()
            doc = SceneDocument(path)
            before = doc.stage.GetRootLayer().ExportToString()
            with self.assertRaises(ValueError):
                doc.edit_transform("/Box", [float("nan"), 0, 0], [0]*3, [1]*3)
            self.assertEqual(before, doc.stage.GetRootLayer().ExportToString())
            self.assertFalse(doc.dirty)
