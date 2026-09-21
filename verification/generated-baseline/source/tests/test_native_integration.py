"""Native integration tests. These exercise real OVRTX/OVStage/Newton/USD
behavior on a supported NVIDIA target and MUST fail (never report passed)
when the required native SDKs or GPU are unavailable, rather than being
skipped. They are separate from the portable generated-suite tests.
"""
import tempfile
import unittest
import uuid

from lertx import host, scene


class NativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        if not host.is_native_supported():
            self.fail(
                "native host support check failed: unsupported OS/interpreter/CPU for native execution"
            )

    def _new_scene_path(self):
        return f"{tempfile.gettempdir()}/lertx-native-test-{uuid.uuid4().hex}.usda"

    def test_default_scene_authors_required_render_and_physics_schemas(self):
        usd_path = self._new_scene_path()
        scene.create_default_scene(usd_path)

        from pxr import Usd, UsdPhysics

        stage = Usd.Stage.Open(usd_path)
        self.assertTrue(stage.GetPrimAtPath("/Render/Product").IsValid())
        self.assertTrue(stage.GetPrimAtPath("/Render/Settings").IsValid())
        self.assertEqual(stage.GetMetadata("renderSettingsPrimPath"), "/Render/Settings")
        sphere = stage.GetPrimAtPath("/World/DynamicSphere")
        self.assertTrue(sphere.HasAPI(UsdPhysics.RigidBodyAPI))
        self.assertTrue(sphere.HasAPI(UsdPhysics.CollisionAPI))

    def test_newton_model_maps_bodies_to_authored_prim_paths(self):
        usd_path = self._new_scene_path()
        scene.create_default_scene(usd_path)

        from pxr import Usd

        stage = Usd.Stage.Open(usd_path)
        _builder, mapping = scene.build_newton_model(stage)
        self.assertIn("/World/DynamicSphere", mapping.index_to_path.values())

    def test_native_worker_full_lifecycle_produces_owned_frame(self):
        usd_path = self._new_scene_path()
        scene.create_default_scene(usd_path)

        worker = scene.NativeWorker(gpu_index=0)
        errors = []
        worker.set_error_handler(errors.append)
        worker.start()
        try:
            worker.submit(lambda: worker.open_usd(usd_path))
            worker.submit(lambda: worker.render("/Render/Product", delta_time=1.0 / 30.0))
        finally:
            worker.stop()

        self.assertEqual(errors, [], f"native worker reported an error: {errors}")
        frame = worker.latest_frame()
        self.assertIsNotNone(frame)
        self.assertGreater(frame.width, 0)
        self.assertGreater(frame.height, 0)


if __name__ == "__main__":
    unittest.main()
