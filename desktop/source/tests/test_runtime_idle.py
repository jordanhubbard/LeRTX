"""Idle behavior is testable without importing or allocating a native runtime."""
import copy
import unittest
from unittest.mock import Mock
from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker


class RuntimeIdleTests(unittest.TestCase):
    def test_paused_scene_settles_then_does_no_native_work(self):
        worker=SceneWorker(copy.deepcopy(DEFAULT_PROFILE))
        worker.physics=Mock()
        worker.render=Mock(return_value=object())
        worker.robot_status=Mock(return_value={'positions':{}})
        worker.publish_transforms=Mock()
        for _ in range(4):self.assertNotIn('unchanged',worker.tick(.02))
        for _ in range(100):self.assertTrue(worker.tick(.02)['unchanged'])
        self.assertEqual(worker.render.call_count,4)
        self.assertEqual(worker.robot_status.call_count,4)
        worker.physics.step.assert_not_called()
        worker.physics.render_matrices.assert_not_called()
        worker.publish_transforms.assert_not_called()
        # Camera/selection publication invalidates the image and settles anew.
        worker._ordinal+=1
        self.assertNotIn('unchanged',worker.tick(.02))
        self.assertEqual(worker.render.call_count,5)
        # Resuming simulation cannot reuse a paused image.
        worker.clock.play()
        self.assertNotIn('unchanged',worker.tick(.02))
        self.assertTrue(worker.physics.step.called)
        self.assertTrue(worker.publish_transforms.called)
