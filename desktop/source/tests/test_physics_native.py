"""Real Newton CUDA acceptance of USD coordinate and collider mapping."""
import os
import unittest
from pathlib import Path

from lertx.physics import PhysicsScene, build_model
from lertx.scene import SimulationDisabledError


class PhysicsNativeTests(unittest.TestCase):
    def fixture(self, name):
        from pxr import Usd
        return Usd.Stage.Open(str(Path(os.environ["LERTX_TEST_SCENES"]) / name))

    def test_centimeters_y_up_parent_scale_and_floor(self):
        sim = PhysicsScene(self.fixture("centimeters-y-up.usda"))
        self.assertEqual(sim.mapping.paths_in_index_order(), ["/World/Assembly/Ball"])
        initial = sim.world_matrices()[0].ExtractTranslation()
        self.assertAlmostEqual(initial[1], 80, places=4)
        for _ in range(480):
            sim.step(1/240, substeps=2)
        final = sim.world_matrices()[0].ExtractTranslation()
        self.assertAlmostEqual(final[0], -20, delta=0.1)
        self.assertAlmostEqual(final[1], 10, delta=1)
        from pxr import Gf
        self.assertEqual(list(Gf.Transform(sim.world_matrices()[0]).GetScale()), [2, 2, 2])
        self.assertAlmostEqual(sim.time, 2)

    def test_unsupported_static_collider_disables_physics(self):
        with self.assertRaisesRegex(SimulationDisabledError, "/World/UnsupportedCollider"):
            build_model(self.fixture("unsupported-collider.usda"))
