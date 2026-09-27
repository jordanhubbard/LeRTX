"""The real renderer must preserve and move the complete nested articulation."""
import copy
from pathlib import Path
import tempfile
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene


class RobotRenderNativeTests(unittest.TestCase):
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
                before=call(lambda:worker.physics.render_matrices())
                call(lambda:worker.command_robot('leader',{'shoulder_pan':.5}))
                call(lambda:worker.set_playing(True))
                for _ in range(70):moving=call(lambda:worker.tick(1/30))
                self.assertAlmostEqual(moving['robots']['positions']['leader']['shoulder_pan'],.5,delta=.05)
                after=call(lambda:worker.physics.render_matrices())
                self.assertGreater(sum(not np.allclose(a,b,atol=.001) for a,b in zip(before,after)),1)
                self.assertGreater(np.abs(pixels(published)-pixels(moving['frame'])).mean(),1.)
                call(lambda:worker.set_playing(False));time=moving['time']
                self.assertEqual(call(lambda:worker.tick(1/30))['time'],time)
                call(worker.reset)
                self.assertAlmostEqual(call(worker.robot_status)['positions']['leader']['shoulder_pan'],0.,delta=1e-5)
            finally:worker.stop()
