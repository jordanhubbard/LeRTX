"""Real rendered scene session; never skip missing GPU/SDK facilities."""
import tempfile
import unittest
from pathlib import Path

from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene


class RuntimeNativeTests(unittest.TestCase):
    def test_render_motion_pause_camera_reset_edit_save_and_close(self):
        import copy
        import numpy as np
        from pxr import Usd, UsdGeom, Sdf

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["rendering"].update(width=320, height=180)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authored.usda"
            create_default_scene(str(path))
            initial_bytes = path.read_bytes()
            worker = SceneWorker(profile)
            errors = []
            worker.set_error_handler(errors.append)
            worker.start()

            def call(fn):
                return worker.submit(fn).result(timeout=120)

            try:
                status = call(lambda: worker.open_document(str(path)))
                self.assertEqual(status["physics_error"], "")
                def quality_token():
                    layer = Sdf.Layer.OpenAsAnonymous(str(worker.runtime_file))
                    snapshot = Usd.Stage.Open(layer)
                    return snapshot.GetPrimAtPath("/Render/Product").GetAttribute("omni:rtx:post:dlss:execMode").Get()
                self.assertEqual(call(quality_token), "balanced")
                first = call(lambda: worker.tick(0))["frame"]
                self.assertEqual((first.width, first.height, first.dtype_name), (320, 180, "uint8"))
                self.assertGreater(np.frombuffer(first.data, dtype=np.uint8).std(), 5)
                malformed = Path(directory)/"malformed.usda"
                malformed.write_text("not a USD scene", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "parse USD"):
                    call(lambda: worker.open_document(str(malformed)))
                self.assertEqual(call(worker.status)["path"], str(path.resolve()))
                self.assertFalse(worker._stop_event.is_set())
                self.assertGreater(len(call(lambda: worker.tick(0))["frame"].data), 0)
                call(lambda: worker.set_playing(True))
                for _ in range(40):
                    moving = call(lambda: worker.tick(1/30))
                pose = call(lambda: list(worker.physics.world_matrices()[0].ExtractTranslation()))
                self.assertAlmostEqual(pose[2], 0.08, delta=0.015)
                self.assertNotEqual(first.data, moving["frame"].data)
                call(lambda: worker.set_playing(False))
                before_time = moving["time"]
                call(lambda: worker.move_camera(orbit=(0.7, 0.2)))
                paused = call(lambda: worker.tick(1/30))
                self.assertEqual(paused["time"], before_time)
                self.assertNotEqual(paused["frame"].data, moving["frame"].data)
                self.assertEqual(path.read_bytes(), initial_bytes)
                def reset_high_quality():
                    worker.profile["rendering"]["quality"] = "high"
                    return worker.reset()
                call(reset_high_quality)
                self.assertEqual(call(quality_token), "quality")
                reset_pose = call(lambda: list(worker.physics.world_matrices()[0].ExtractTranslation()))
                self.assertAlmostEqual(reset_pose[2], 0.5, places=5)
                call(lambda: worker.edit("/World/DynamicSphere", [0, 0, 0.7], [0, 0, 0], [1, 1, 1]))
                self.assertEqual(path.read_bytes(), initial_bytes)
                candidate = copy.deepcopy(worker.profile)
                candidate["rendering"].update(width=384, height=216)
                candidate["physics"]["timestep_hz"] = 120
                configured = call(lambda: worker.configure(candidate, str(Path(directory)/"settings.json")))
                self.assertTrue(configured["dirty"])
                self.assertFalse(configured["playing"])
                self.assertEqual(call(lambda: worker.inspect("/World/DynamicSphere"))["translation"][2], .7)
                resized = call(lambda: worker.tick(0))["frame"]
                self.assertEqual((resized.width, resized.height), (384, 216))
                self.assertEqual(path.read_bytes(), initial_bytes)
                from unittest.mock import patch
                rejected = copy.deepcopy(candidate)
                rejected["rendering"]["width"] = 512
                settings_before = (Path(directory)/"settings.json").read_bytes()
                with patch("lertx.config.save_profile", side_effect=OSError("injected save failure")):
                    with self.assertRaisesRegex(ValueError, "previous configuration restored"):
                        call(lambda: worker.configure(rejected, str(Path(directory)/"settings.json")))
                self.assertEqual((Path(directory)/"settings.json").read_bytes(), settings_before)
                self.assertTrue(call(worker.status)["dirty"])
                restored = call(lambda: worker.tick(0))["frame"]
                self.assertEqual((restored.width, restored.height), (384, 216))
                self.assertFalse(worker._stop_event.is_set())
                status = call(worker.save)
                self.assertFalse(status["dirty"])
                disk = Usd.Stage.Open(Sdf.Layer.OpenAsAnonymous(str(path)))
                z = UsdGeom.Xformable(disk.GetPrimAtPath("/World/DynamicSphere")).GetLocalTransformation().ExtractTranslation()[2]
                self.assertAlmostEqual(z, 0.7)
                self.assertFalse(disk.GetPrimAtPath(worker.camera_path))
                call(lambda: worker.open_document(str(path)))
                self.assertEqual(call(lambda: worker.tick(0))["time"], 0)
            finally:
                worker.stop()
            self.assertEqual(errors, [])
            self.assertIsNone(worker._renderer)
            self.assertIsNone(worker._stage)
            self.assertIsNone(worker._temporary)
            self.assertIsNone(worker._thread)
