"""Qt tests for the always-visible leader/follower joint slider grid."""
import copy
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lertx import config, ui
from lertx.robot import JOINT_NAMES, home_positions


def _build_window():
    ui.build_application([])
    return ui.build_main_window(
        copy.deepcopy(config.DEFAULT_PROFILE),
        worker_factory=lambda: (_ for _ in ()).throw(RuntimeError("no native worker in this test")),
        default_scene_path="unused.usda",
        config_path="/tmp/lertx-robot-ui-test-settings.json",
    )


class RobotPanelTests(unittest.TestCase):
    def setUp(self):
        self.owner = _build_window()
        self.owner._frame_timer.stop()
        self.panel = self.owner.robot_panel

    def tearDown(self):
        self.owner.deleteLater()

    def test_all_twelve_joints_are_labeled_and_present(self):
        for role in ('leader', 'follower'):
            for name in JOINT_NAMES:
                self.assertIn((role, name), self.panel.sliders)
                self.assertIn((role, name), self.panel.values)

    def test_disabled_until_positions_available(self):
        self.assertFalse(self.panel.isEnabled())
        self.panel.update_state({'positions': {'leader': home_positions('leader')}, 'following': True})
        self.assertTrue(self.panel.isEnabled())

    def test_gripper_slider_maps_to_percent_spinbox(self):
        self.owner._ready = True
        self.panel.update_state({'positions': {'leader': home_positions('leader')}, 'following': True})
        self.panel.sliders['leader', 'gripper'].setValue(500)
        self.assertAlmostEqual(self.panel.values['leader', 'gripper'].value(), 50., places=1)
        self.assertEqual(self.panel.values['leader', 'gripper'].suffix(), ' %')
        self.assertEqual(self.owner.viewport_label.intent[:2], ('leader', 'gripper'))
        self.owner._ready = False

    def test_typing_a_value_drives_the_same_intent_as_the_slider(self):
        self.owner._ready = True
        self.panel.update_state({'positions': {'leader': home_positions('leader')}, 'following': True})
        self.panel.values['leader', 'shoulder_pan'].setValue(30.)
        self.assertAlmostEqual(self.owner.viewport_label.intent[2], math.radians(30.))
        low, high = self.panel._range['leader', 'shoulder_pan']
        fraction = (math.radians(30.) - low) / (high - low)
        self.assertAlmostEqual(self.panel.sliders['leader', 'shoulder_pan'].value(), round(1000 * fraction))
        self.owner._ready = False

    def test_follower_sliders_lock_while_following_and_unlock_when_unchecked(self):
        state = {'positions': {'follower': home_positions('follower')}, 'following': True}
        self.panel.update_state(state)
        self.assertFalse(self.panel.sliders['follower', 'wrist_roll'].isEnabled())
        state = {'positions': {'follower': home_positions('follower')}, 'following': False}
        self.panel.update_state(state)
        self.assertTrue(self.panel.sliders['follower', 'wrist_roll'].isEnabled())

    def test_live_hardware_view_locks_every_slider_for_that_role(self):
        state = {'positions': {'leader': home_positions('leader')}, 'following': True, 'live_roles': ['leader']}
        self.panel.update_state(state)
        self.assertFalse(self.panel.sliders['leader', 'shoulder_pan'].isEnabled())

    def test_dragging_a_slider_does_not_require_the_worker_to_be_idle(self):
        self.owner._ready = True
        self.owner._pending = [object()]
        self.panel.update_state({'positions': {'leader': home_positions('leader')}, 'following': True})
        low, high = self.panel._range['leader', 'shoulder_lift']
        self.panel.sliders['leader', 'shoulder_lift'].setValue(1000)
        self.assertEqual(self.owner.viewport_label.intent, ('leader', 'shoulder_lift', high))
        self.owner._pending = []
        self.owner._ready = False


class RobotPosePresetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = str(Path(self.directory.name) / 'settings.json')
        ui.build_application([])
        self.owner = ui.build_main_window(
            copy.deepcopy(config.DEFAULT_PROFILE),
            worker_factory=lambda: (_ for _ in ()).throw(RuntimeError("no native worker in this test")),
            default_scene_path="unused.usda",
            config_path=self.config_path,
        )
        self.owner._frame_timer.stop()
        self.panel = self.owner.robot_panel
        self.addCleanup(self.owner.deleteLater)

    def test_bundled_presets_are_listed(self):
        labels = [self.panel.preset_combo.itemText(i) for i in range(self.panel.preset_combo.count())]
        self.assertIn('Danger', labels)
        self.assertIn('The Signal', labels)

    def test_save_and_load_round_trip(self):
        self.owner._ready = True
        low, high = self.panel._range['leader', 'shoulder_pan']
        leader = dict(home_positions('leader'), shoulder_pan=low + (high - low) * .75)
        # save_preset reads the confirmed server-reported state (self.state), the same
        # value the live frame loop keeps in sync after a drag — not the raw widget value.
        self.panel.update_state({'positions': {'leader': leader, 'follower': home_positions('follower')},
                                  'following': True})

        with patch('PySide6.QtWidgets.QInputDialog.getText', return_value=('Test Pose', True)):
            self.panel.save_preset()

        saved_path = Path(self.directory.name) / 'poses' / 'Test Pose.json'
        self.assertTrue(saved_path.is_file())
        labels = [self.panel.preset_combo.itemText(i) for i in range(self.panel.preset_combo.count())]
        self.assertIn('Test Pose (custom)', labels)

        calls = []
        def command_robot(role, positions=None, following=None):
            calls.append((role, positions, following))
            return {}
        self.owner.worker = SimpleNamespace(command_robot=command_robot)
        self.owner._command = lambda fn, callback=None: (callback(fn()) if callback else fn())
        self.owner._apply_status = lambda status: None
        self.owner._pending = []
        self.panel.preset_combo.setCurrentIndex(self.panel.preset_combo.findText('Test Pose (custom)'))
        self.panel.load_preset()

        self.assertEqual(calls[0][0], 'leader')
        self.assertAlmostEqual(calls[0][1]['shoulder_pan'], low + (high - low) * .75, places=3)
        self.assertEqual(calls[0][2], False)
        self.assertEqual(calls[1][0], 'follower')
        self.owner._ready = False


if __name__ == '__main__':
    unittest.main()
