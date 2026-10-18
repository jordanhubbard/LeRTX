"""The real renderer must preserve and move the complete nested articulation."""
import copy
from pathlib import Path
import tempfile
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene


class RobotRenderNativeTests(unittest.TestCase):
    def test_readonly_measured_motion_is_visible_beyond_simulation_limits(self):
        import time
        import numpy as np
        from lertx.robot import home_positions,joint_limits
        profile=copy.deepcopy(DEFAULT_PROFILE);profile['rendering'].update(width=480,height=300)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'measured.usdc';create_default_scene(str(path),include_robots=True)
            worker=SceneWorker(profile);worker.start()
            def call(fn):return worker.submit(fn).result(timeout=120)
            def pixels(result):
                frame=result['frame']
                return np.frombuffer(frame.data,dtype=np.uint8).reshape(frame.height,frame.width,frame.channels)[...,:3].astype(float)
            try:
                call(lambda:worker.open_document(str(path)))
                for _ in range(4):call(lambda:worker.tick(0.))
                for role in ('leader','follower'):
                    pose=home_positions(role)
                    before=call(lambda:worker.hardware_pose(role,pose,time.monotonic(),display_only=True))
                    pose={**pose,'shoulder_pan':.6,'elbow_flex':joint_limits(role)['elbow_flex'][0]-.12}
                    with self.assertRaises(ValueError):call(lambda:worker.hardware_pose(role,pose,time.monotonic()))
                    after=call(lambda:worker.hardware_pose(role,pose,time.monotonic(),display_only=True))
                    for _ in range(3):after=call(lambda:worker.tick(0.))
                    self.assertAlmostEqual(after['robots']['positions'][role]['shoulder_pan'],.6,delta=.01)
                    self.assertAlmostEqual(after['robots']['positions'][role]['elbow_flex'],pose['elbow_flex'],delta=.01)
                    target=call(lambda:worker.physics.targets[role]['elbow_flex'])
                    self.assertAlmostEqual(target,joint_limits(role)['elbow_flex'][0])
                    difference=np.mean(np.max(np.abs(pixels(after)-pixels(before)),axis=2)>20)
                    self.assertGreater(difference,.005,f'{role}: before std={pixels(before).std()}, after std={pixels(after).std()}')
            finally:worker.stop()

    def test_nested_geometry_survives_publication_and_tracks_dynamics(self):
        import numpy as np
        profile=copy.deepcopy(DEFAULT_PROFILE);profile['rendering'].update(width=480,height=300)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pair.usdc';create_default_scene(str(path),include_robots=True)
            worker=SceneWorker(profile);worker.start()
            def call(fn):return worker.submit(fn).result(timeout=120)
            def pixels(frame):return np.frombuffer(frame.data,dtype=np.uint8).reshape(frame.height,frame.width,frame.channels)[...,:3].astype(float)
            try:
                call(lambda:worker.open_document(str(path)))
                for _ in range(3):authored=call(lambda:worker.render('/Render/Product',0))
                call(lambda:worker.publish_transforms(worker.physics.render_mapping,worker.physics.render_matrices()))
                for _ in range(3):published=call(lambda:worker.tick(0))['frame']
                # At rest publication must preserve complete geometry. Previously
                # updating only ancestor Xforms using world matrices separated the nested arms.
                self.assertLess(np.abs(pixels(authored)-pixels(published)).mean(),3.)
                # Selection must not pin a stale mesh transform while ancestors move.
                call(lambda:worker.select_joint('leader','shoulder_pan'))
                before=call(lambda:worker.physics.render_matrices())
                call(lambda:worker.command_robot('leader',{'shoulder_pan':.5}))
                call(lambda:worker.set_playing(True))
                for _ in range(70):moving=call(lambda:worker.tick(1/30))
                self.assertAlmostEqual(moving['robots']['positions']['leader']['shoulder_pan'],.5,delta=.05)
                after=call(lambda:worker.physics.render_matrices())
                self.assertGreater(sum(not np.allclose(a,b,atol=.001) for a,b in zip(before,after)),1)
                self.assertGreater(np.abs(pixels(published)-pixels(moving['frame'])).mean(),1.)
                # Clearing the outline also touches renderer mesh state; motion must
                # continue afterward, without reconstructing the renderer.
                call(lambda:worker.select(None))
                call(lambda:worker.command_robot('leader',{'shoulder_pan':-.5}))
                for _ in range(70):cleared=call(lambda:worker.tick(1/30))
                self.assertAlmostEqual(cleared['robots']['positions']['leader']['shoulder_pan'],-.5,delta=.05)
                self.assertGreater(np.mean(np.abs(pixels(cleared['frame'])-pixels(moving['frame']))>30),.005)
                call(lambda:worker.set_playing(False));time=cleared['time']
                self.assertEqual(call(lambda:worker.tick(1/30))['time'],time)
                call(worker.reset)
                self.assertAlmostEqual(call(worker.robot_status)['positions']['leader']['shoulder_pan'],0.,delta=1e-5)
            finally:worker.stop()
