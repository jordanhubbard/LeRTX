"""Qt control integration with the actual GPU worker and framebuffer."""
import copy
import os
from pathlib import Path
import tempfile
import time
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene
from lertx.ui import build_application, build_main_window


class WindowNativeTests(unittest.TestCase):
    def test_visible_controls_deliver_native_frames_and_save(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        app = build_application([])
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["rendering"].update(width=640, height=360, target_fps=15)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.usda"
            create_default_scene(str(path))
            window = build_main_window(profile, lambda: SceneWorker(profile),
                                       str(path), str(Path(directory)/"settings.json"))
            window.show()
            window.open_scene(str(path))

            def wait(predicate, timeout=90):
                deadline = time.monotonic()+timeout
                while time.monotonic() < deadline:
                    app.processEvents()
                    if predicate():
                        return
                    # qWait's C++ sleep can retain the GIL, starving the Python
                    # native owner. Real QApplication.exec releases it; emulate
                    # that between bounded event processing passes here.
                    time.sleep(0.02)
                self.fail(f"UI condition timed out: {window.native_status_label.text()}")

            try:
                wait(lambda: window._image is not None)
                self.assertTrue(window.isVisible())
                self.assertGreaterEqual(window.tree.width(), 175)
                self.assertLessEqual(window.inspector.width(), 420)
                self.assertIn("gpu", window._diagnostics)
                self.assertIn("ovrtx", window._diagnostics)
                self.assertFalse(window.viewport_label.pixmap().isNull())
                malformed = Path(directory)/"bad.usda"
                malformed.write_text("invalid USD", encoding="utf-8")
                window.open_scene(str(malformed))
                wait(lambda: "Could not parse USD" in window.native_status_label.text())
                self.assertTrue(window._ready)
                self.assertEqual(window.current_scene_path, str(path.resolve()))
                QTest.mouseClick(window.play_button, Qt.MouseButton.LeftButton)
                wait(lambda: window.clock.sim_time > 0.15)
                QTest.mouseClick(window.play_button, Qt.MouseButton.LeftButton)
                wait(lambda: not window.clock.playing)
                paused = window.clock.sim_time
                QTest.qWait(200)
                self.assertEqual(window.clock.sim_time, paused)
                QTest.mouseClick(window.reset_button, Qt.MouseButton.LeftButton)
                wait(lambda: window._ready and window.clock.sim_time == 0)
                self.assertEqual(window.statusBar().currentMessage(), "")
                sphere_item = window._tree_items["/World/DynamicSphere"]
                self.assertIs(sphere_item.parent(), window._tree_items["/World"])
                window.tree.setCurrentItem(sphere_item)
                wait(lambda: window.inspector.apply_button.isEnabled())
                window.inspector.translate[2].setValue(0.9)
                QTest.mouseClick(window.inspector.apply_button, Qt.MouseButton.LeftButton)
                wait(lambda: window.has_unsaved_changes and window._ready)
                window._on_save()
                wait(lambda: not window.has_unsaved_changes)
                self.assertIn("0.9", path.read_text())
                window.search_edit.setFocus()
                QTest.keyClicks(window.search_edit, "DynamicSphere")
                self.assertEqual(window.search_edit.text(), "DynamicSphere")
                screenshot = os.environ.get("LERTX_UI_SCREENSHOT")
                if screenshot:
                    self.assertTrue(window.grab().save(screenshot))
            finally:
                window.has_unsaved_changes = False
                window.close()
                wait(lambda: not window.isVisible())
            self.assertIsNone(window.worker)
