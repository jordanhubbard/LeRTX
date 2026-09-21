import copy
import json
from pathlib import Path
import tempfile
import unittest

from lertx.document import SceneDocument
from lertx.reconstruction import build_draft_stage
from tests.test_reconstruction import scene_payload


class ReconstructionNativeTests(unittest.TestCase):
    def test_draft_renders_and_edits_without_claiming_physics(self):
        import numpy as np
        from lertx.config import DEFAULT_PROFILE
        from lertx.runtime import SceneWorker
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["rendering"].update(width=320, height=180)
        stage = build_draft_stage(json.dumps(scene_payload()), "c"*64, "test/model")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"draft.usda"
            stage.GetRootLayer().Export(str(path))
            worker = SceneWorker(profile)
            worker.start()
            def call(operation):
                return worker.submit(operation).result(timeout=120)
            try:
                status = call(lambda: worker.open_document(str(path)))
                self.assertIn("No supported rigid bodies", status["physics_error"])
                first = call(lambda: worker.tick(0))["frame"]
                self.assertGreater(np.frombuffer(first.data, dtype=np.uint8).std(), 5)
                call(lambda: worker.edit("/World/Objects/table", [0,0,.8], [0,0,30], [1,.6,.05]))
                self.assertTrue(call(worker.status)["dirty"])
                call(worker.save)
                # Keep the owning stage alive while reading its prim metadata.
                document = SceneDocument(path)
                self.assertEqual(document.stage.GetPrimAtPath("/World").GetAttribute("lertx:reconstructionStatus").Get(), "unverified")
                self.assertFalse(call(worker.status)["playing"])
            finally:
                worker.stop()

    def test_edit_save_reopen_preserves_geometry_and_unverified_provenance(self):
        from pxr import UsdGeom, UsdPhysics
        payload = scene_payload()
        sphere = copy.deepcopy(payload["objects"][0])
        sphere.update(id="ball", geometry={"type": "sphere", "radius": .1})
        mesh = copy.deepcopy(sphere)
        mesh.update(id="obstacle", geometry={"type": "mesh", "points": [[0,0,0],[1,0,0],[0,1,0]],
                                            "triangles": [0,1,2]})
        payload["objects"].extend([sphere, mesh])
        stage = build_draft_stage(json.dumps(payload), "a"*64, "test/model")
        self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage), 1.)
        self.assertEqual(UsdGeom.GetStageUpAxis(stage), "Z")
        for prim in stage.Traverse():
            self.assertFalse(prim.HasAPI(UsdPhysics.CollisionAPI))
            self.assertFalse(prim.HasAPI(UsdPhysics.RigidBodyAPI))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"draft.usda"
            self.assertTrue(stage.GetRootLayer().Export(str(path)))
            doc = SceneDocument(path)
            for actual, expected in zip(doc.transform("/World/Objects/table")["scale"], [1, .6, .05]):
                self.assertAlmostEqual(actual, expected, places=6)
            doc.edit_transform("/World/Objects/ball", [1,2,3], [10,20,30], [1,1,1])
            doc.save(Path(directory)/"edited.usdc")
            reopened = SceneDocument(Path(directory)/"edited.usdc")
            self.assertEqual(reopened.transform("/World/Objects/ball")["translation"], [1,2,3])
            world = reopened.stage.GetPrimAtPath("/World")
            self.assertEqual(world.GetAttribute("lertx:reconstructionStatus").Get(), "unverified")
            self.assertEqual(world.GetAttribute("lertx:dimensionSource").Get(), "estimated")
            self.assertEqual(world.GetAttribute("lertx:sourceImageSHA256").Get(), "a"*64)
            self.assertEqual(list(world.GetAttribute("lertx:unobserved").Get()), ["Behind the workbench"])
            self.assertEqual(list(UsdGeom.Mesh(reopened.stage.GetPrimAtPath("/World/Objects/obstacle")).GetFaceVertexIndicesAttr().Get()), [0,1,2])

    def test_bad_response_does_not_change_existing_stage(self):
        stage = build_draft_stage(json.dumps(scene_payload()), "b"*64, "test/model")
        before = stage.GetRootLayer().ExportToString()
        with self.assertRaises(ValueError):
            build_draft_stage('{"python":"do something"}', "b"*64, "test/model")
        self.assertEqual(stage.GetRootLayer().ExportToString(), before)
