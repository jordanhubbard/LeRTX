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

    def test_play_without_native_scene_does_not_claim_simulation(self):
        window = _build_window()
        self.assertFalse(window.clock.playing)
        window.play_button.click()
        self.assertFalse(window.clock.playing)
        self.assertEqual(window.play_button.text(), "Play")

    def test_reset_button_zeroes_sim_time_label(self):
        window = _build_window()
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

    def test_nested_hierarchy_search_preserves_ancestors_and_expansion(self):
        window = _build_window()
        hierarchy = [{"path":p,"type":"Xform"} for p in
                     ("/World/Arm/Joint", "/World/Table", "/World", "/World/Arm")]
        window._rebuild_hierarchy(hierarchy)
        nodes = window._tree_items
        self.assertEqual(window.tree.topLevelItemCount(), 1)
        self.assertIs(nodes["/World/Arm/Joint"].parent(), nodes["/World/Arm"])
        self.assertEqual(nodes["/World/Arm/Joint"].toolTip(0), "/World/Arm/Joint")
        nodes["/World/Arm"].setExpanded(False)
        window._on_search_changed("joint")
        self.assertFalse(nodes["/World"].isHidden())
        self.assertFalse(nodes["/World/Arm"].isHidden())
        self.assertTrue(nodes["/World/Arm"].isExpanded())
        self.assertTrue(nodes["/World/Table"].isHidden())
        window._on_search_changed("")
        self.assertFalse(nodes["/World/Arm"].isExpanded())
        self.assertFalse(nodes["/World/Table"].isHidden())
        window.close()

    def test_filtering_selected_prim_clears_unsafe_hidden_selection(self):
        window = _build_window()
        window._rebuild_hierarchy([{"path":p,"type":"Xform"} for p in
                                   ("/World", "/World/Arm", "/World/Table")])
        window.tree.setCurrentItem(window._tree_items["/World/Arm"])
        window.inspector.show_prim("/World/Arm", "Xform", True)
        window._on_search_changed("Table")
        self.assertIsNone(window._selected_path())
        self.assertFalse(window.inspector.apply_button.isEnabled())
        self.assertEqual(window.inspector.path_label.text(), "")
        window.close()

    def test_hierarchy_rebuild_preserves_selection_by_full_path(self):
        window = _build_window()
        hierarchy = [{"path":p,"type":"Xform"} for p in
                     ("/World", "/World/Arm", "/World/Arm/Joint")]
        window._rebuild_hierarchy(hierarchy)
        window._tree_items["/World/Arm"].setExpanded(True)
        window.tree.setCurrentItem(window._tree_items["/World/Arm/Joint"])
        window._rebuild_hierarchy(hierarchy + [{"path":"/World/Table", "type":"Cube"}])
        self.assertEqual(window._selected_path(), "/World/Arm/Joint")
        self.assertTrue(window._tree_items["/World/Arm"].isExpanded())
        window.close()

    def test_transform_fields_fit_large_values_at_small_window_size(self):
        application = ui.build_application([])
        window = _build_window()
        window.resize(1024, 768)
        window.show()
        try:
            for spin in window.inspector.translate + window.inspector.rotate + window.inspector.scale:
                spin.setValue(-1000000)
            application.processEvents()
            for spin in window.inspector.translate + window.inspector.rotate + window.inspector.scale:
                self.assertGreaterEqual(spin.lineEdit().width(), spin.fontMetrics().horizontalAdvance(spin.text()))
                self.assertIn(spin.accessibleName()[0], "XYZ")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
