import time
import unittest

from lertx.mock_ui import build_mock_dialog
from lertx.ui import build_application


class MockUiTests(unittest.TestCase):
    def test_independent_connections_pose_freeze_and_cleanup(self):
        application = build_application([])
        dialog = build_mock_dialog()
        dialog.show()
        try:
            self.assertIn("SIMULATED", dialog.windowTitle())
            leader, freeze, joints, gripper = dialog.controls["leader"]
            leader.click()
            joints[0].setValue(42)
            gripper.setValue(80)
            dialog.poll()
            self.assertEqual(dialog.streams["leader"].latest.degrees[0], 42)
            self.assertEqual(dialog.streams["leader"].latest.gripper_percent, 80)
            self.assertEqual(dialog.streams["follower"].state, "disconnected")
            frozen_sample = dialog.streams["leader"].latest
            freeze.click()
            joints[0].setValue(-80)
            deadline = time.monotonic()+3
            while time.monotonic() < deadline and dialog.streams["leader"].state != "stale":
                application.processEvents()
                time.sleep(.01)
            dialog.poll()
            self.assertIs(dialog.streams["leader"].latest, frozen_sample)
            self.assertIn("stale", dialog.statuses["leader"].text())
            dialog.controls["follower"][0].click()
            self.assertEqual(dialog.streams["follower"].state, "live")
            leader.click()
            self.assertEqual(dialog.streams["leader"].state, "disconnected")
            freeze.click()
            leader.click()
            self.assertEqual(dialog.streams["leader"].latest.degrees[0], -80)
        finally:
            dialog.reject()
        self.assertFalse(dialog.timer.isActive())
        self.assertTrue(all(not reader.connected for reader in dialog.readers.values()))
        dialog.deleteLater()
        application.processEvents()
