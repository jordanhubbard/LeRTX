"""Native CUDA articulation tests; missing SDK/GPU is a failure, not a skip."""
import math
import tempfile
from pathlib import Path
import unittest

from pxr import Usd, UsdGeom
from lertx.physics import PhysicsScene
from lertx.scene import create_default_scene
from lertx.robot import JOINT_NAMES, home_positions, follower_targets


class RobotDynamicsTests(unittest.TestCase):
    def test_gravity_tracking_following_base_and_authored_reset(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pair.usdc';create_default_scene(str(path),include_robots=True)
            stage=Usd.Stage.Open(str(path));authored=path.read_bytes();sim=PhysicsScene(stage)
            initial=sim.state.body_q.numpy().copy()
            # All initial body poses must match the actual saved USD hierarchy.
            for name,matrix in zip(sim.mapping.paths_in_index_order(),sim.world_matrices()):
                np.testing.assert_allclose(matrix,UsdGeom.Xformable(stage.GetPrimAtPath(name)).ComputeLocalToWorldTransform(0),atol=1e-6)
            target=home_positions('leader');target.update(shoulder_pan=.4,elbow_flex=-.2,wrist_roll=.3)
            sim.command_robot('leader',target)
            for _ in range(480):sim.step(1/120)
            positions=sim.robot_positions()
            for name in JOINT_NAMES:
                self.assertAlmostEqual(positions['leader'][name],target[name],delta=.04,msg=name)
                self.assertAlmostEqual(positions['follower'][name],follower_targets(positions['leader'])[name],delta=.055,msg=name)
            for role,data in sim.robots.items():
                np.testing.assert_allclose(sim.state.body_q.numpy()[data['bodies']['base_link']],initial[data['bodies']['base_link']],atol=1e-6)
            with self.assertRaises(ValueError):sim.command_robot('leader',{'shoulder_pan':100})
            with self.assertRaises(ValueError):sim.command_robot('leader',{'gripper':float('nan')})
            with self.assertRaises(ValueError):sim.command_robot('follower',{'shoulder_pan':0})
            sim.command_robot('leader',following=False);sim.command_robot('follower',{'shoulder_pan':-.25})
            for _ in range(360):sim.step(1/120)
            self.assertAlmostEqual(sim.robot_positions()['follower']['shoulder_pan'],-.25,delta=.04)
            self.assertEqual(path.read_bytes(),authored)
            reset=PhysicsScene(Usd.Stage.Open(str(path)))
            for role,values in reset.robot_positions().items():
                for name in JOINT_NAMES:self.assertAlmostEqual(values[name],home_positions(role)[name],delta=1e-5)
