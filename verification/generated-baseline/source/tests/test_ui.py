"""Qt UI tests exercising real visible controls. These require PySide6 and
MUST fail (never report passed) when it is unavailable, rather than
skipping. Portable tests remain in the other test modules.
"""
import copy
import unittest

from lertx import config
from lertx import ui


def _build_window():
    ui.build_application([])
    return ui.build_main_window(
        copy.deepcopy(config.DEFAULT_PROFILE),
        worker_factory=lambda: (_ for _ in ()).throw(RuntimeError("no native worker in this test")),
        default_scene_path="unused.usda",
        config_path="/tmp/lertx-ui-test-settings.json",
    )


class MainWindowTests(unittest.TestCase):
    def test_main_window_has_required_title_and_controls(self):
        window = _build_window()
        self.assertEqual(window.windowTitle(), "LeRTX")
        self.assertEqual(window.play_button.text(), "Play")
        self.assertEqual(window.reset_button.text(), "Reset")

    def test_play_pause_toggles_button_label_and_clock_state(self):
        window = _build_window()
        self.assertFalse(window.clock.playing)
        window.play_button.click()
        self.assertTrue(window.clock.playing)
        self.assertEqual(window.play_button.text(), "Pause")
        window.play_button.click()
        self.assertFalse(window.clock.playing)
        self.assertEqual(window.play_button.text(), "Play")

    def test_reset_button_zeroes_sim_time_label(self):
        window = _build_window()
        window.clock.play()
        window.clock.advance(1.0)
        window.reset_button.click()
        self.assertEqual(window.sim_time_label.text(), "t=0.00s")

    def test_search_field_hides_non_matching_hierarchy_items(self):
        from PySide6.QtWidgets import QTreeWidgetItem

        window = _build_window()
        window.tree.addTopLevelItem(QTreeWidgetItem(["WorkSurface"]))
        window.tree.addTopLevelItem(QTreeWidgetItem(["DynamicSphere"]))
        window.search_edit.setText("Sphere")
        window._on_search_changed("Sphere")
        self.assertTrue(window.tree.topLevelItem(0).isHidden())
        self.assertFalse(window.tree.topLevelItem(1).isHidden())

    def test_inspector_disabled_until_selection(self):
        window = _build_window()
        self.assertFalse(window.inspector.translate[0].isEnabled())


if __name__ == "__main__":
    unittest.main()
