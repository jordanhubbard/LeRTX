"""Actual photo dialog, asynchronous Responses path, USD adoption and RTX window."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from lertx.config import DEFAULT_PROFILE
from lertx.document import SceneDocument
from lertx.photo import request_scene
from lertx.photo_ui import build_photo_dialog
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene
from lertx.ui import build_application, build_main_window
from tests.test_reconstruction import scene_payload


class PhotoWindowNativeTests(unittest.TestCase):
    def test_failed_reconstruction_preserves_dirty_workspace_and_rendering(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QImage
        from lertx.transport import TimeoutTransportError
        application = build_application([])
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["llm"]["api_key"] = "injected-test-key"
        profile["rendering"].update(width=320, height=180, target_fps=10)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/"existing.usda"
            create_default_scene(str(source))
            disk_before = source.read_bytes()
            image = QImage(100,100,QImage.Format.Format_RGB888)
            image.fill(0x88aacc)
            self.assertTrue(image.save(str(root/"photo.png")))
            window = build_main_window(profile, lambda: SceneWorker(profile), str(source), str(root/"settings.json"))
            window.show()
            window.open_scene(str(source))
            def wait(predicate):
                deadline = time.monotonic()+90
                while time.monotonic() < deadline:
                    application.processEvents()
                    if predicate():
                        return
                    time.sleep(.02)
                self.fail(window.native_status_label.text())
            try:
                wait(lambda: window._ready and not window._pending)
                window._command(lambda: window.worker.edit("/World/DynamicSphere", [0,0,.9], [0,0,0], [1,1,1]),
                                window._apply_status)
                wait(lambda: window.has_unsaved_changes and not window._pending)
                def authored():
                    return window.worker.document.stage.GetRootLayer().ExportToString()
                before = window.worker.submit(authored).result(timeout=120)
                for failure, message in (("malformed", "valid scene"), ("incomplete", "truncated"),
                                         ("auth", "Authentication failed"), ("timeout", "timed out")):
                    with self.subTest(failure=failure):
                        observed = []
                        def transport(*args):
                            if failure == "timeout":
                                raise TimeoutTransportError("private-provider-detail")
                            if failure == "auth":
                                return 401, {}, b"private-provider-detail"
                            response = {"status":"incomplete" if failure == "incomplete" else "completed",
                                "output":[{"type":"message", "content":[{"type":"output_text",
                                "text":"private-provider-detail: not scene JSON"}]}]}
                            return 200, {}, json.dumps(response).encode()
                        window.reconstruction_probe.tester = lambda p, image, cancel_token: request_scene(
                            p, image, transport=transport, cancel_token=cancel_token)
                        def automated_dialog(*args, **kwargs):
                            dialog = build_photo_dialog(*args, **kwargs)
                            def submit():
                                dialog.select_photo(root/"photo.png")
                                dialog.upload_button.click()
                            monitor = QTimer(dialog)
                            def inspect_result():
                                if dialog.ticket is not None and not dialog.timer.isActive():
                                    observed.append((dialog.status.text(), dialog.result_scene))
                                    monitor.stop()
                                    dialog.reject()
                            monitor.timeout.connect(inspect_result)
                            monitor.start(50)
                            QTimer.singleShot(20, dialog, submit)
                            QTimer.singleShot(10000, dialog, dialog.reject)
                            return dialog
                        with patch("lertx.photo_ui.build_photo_dialog", side_effect=automated_dialog), \
                                patch.object(window.worker, "import_photo_draft", wraps=window.worker.import_photo_draft) as adopt:
                            window._on_photo()
                            wait(lambda: bool(observed) and not window._pending)
                            adopt.assert_not_called()
                        self.assertIn(message, observed[0][0])
                        self.assertNotIn("private-provider-detail", observed[0][0])
                        self.assertIsNone(observed[0][1])
                        self.assertEqual(window.current_scene_path, str(source.resolve()))
                        self.assertTrue(window.has_unsaved_changes)
                        self.assertEqual(window.worker.submit(authored).result(timeout=120), before)
                        self.assertEqual(source.read_bytes(), disk_before)
                        previous_frame = window._image.cacheKey()
                        window._camera(orbit=(.03,0))  # Idle scenes render on demand.
                        wait(lambda: window._image.cacheKey() != previous_frame)
                        self.assertFalse(window.viewport_label.pixmap().isNull())
            finally:
                window.has_unsaved_changes = False
                window.close()
                wait(lambda: not window.isVisible())

    def test_preview_upload_adopt_render_save_and_reopen(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QFileDialog
        application = build_application([])
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["llm"]["api_key"] = "injected-test-key"
        profile["rendering"].update(width=320, height=180, target_fps=10)
        calls = []
        def transport(url, headers, body, timeout):
            calls.append(json.loads(body))
            return 200, {}, json.dumps({"status":"completed", "output":[{"type":"message",
                "content":[{"type":"output_text", "text":json.dumps(scene_payload())}]}]}).encode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/"initial.usda"
            create_default_scene(str(source))
            image = QImage(100,100,QImage.Format.Format_RGB888)
            image.fill(0x88aacc)
            image.save(str(root/"photo.png"))
            window = build_main_window(profile, lambda: SceneWorker(profile), str(source), str(root/"settings.json"))
            window.reconstruction_probe.tester = lambda profile, image, cancel_token: request_scene(
                profile, image, transport=transport, cancel_token=cancel_token)
            window.show()
            window.open_scene(str(source))
            def wait(predicate):
                deadline = time.monotonic()+90
                while time.monotonic() < deadline:
                    application.processEvents()
                    if predicate():
                        return
                    time.sleep(.02)
                self.fail(window.native_status_label.text())
            def automated_dialog(*args, **kwargs):
                dialog = build_photo_dialog(*args, **kwargs)
                def submit():
                    dialog.select_photo(root/"photo.png")
                    dialog.upload_button.click()
                monitor=QTimer(dialog)
                def review():
                    if dialog.result_scene is not None:
                        monitor.stop()
                        self.assertEqual(dialog.focus_choice.currentData(),'table')
                        dialog.review_button.click()
                monitor.timeout.connect(review);monitor.start(40)
                QTimer.singleShot(20, submit)
                QTimer.singleShot(10000, dialog, dialog.reject)
                return dialog
            try:
                wait(lambda: window._image is not None)
                before_pixels = bytes(window._image.constBits())
                with patch("lertx.photo_ui.build_photo_dialog", side_effect=automated_dialog):
                    window._on_photo()
                    wait(lambda: window.reconstruction_warning.isVisible() and window.has_unsaved_changes)
                self.assertEqual(len(calls), 1)
                self.assertTrue(window.requires_save_as)
                self.assertNotEqual(window.current_scene_path, str(source))
                self.assertFalse(window.play_button.isEnabled())
                draft_path = Path(window.current_scene_path)
                wait(lambda: window._ready and not window._pending)
                adopted_frame_key = window._image.cacheKey()
                window._camera(orbit=(.03,0))
                wait(lambda: window._image.cacheKey() != adopted_frame_key
                     and bytes(window._image.constBits()) != before_pixels)
                draft_pixels = bytes(window._image.constBits())
                self.assertGreater(len(set(draft_pixels)), 16)
                self.assertFalse(window.viewport_label.pixmap().isNull())
                destination = root/"saved-draft.usda"
                with patch.object(QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
                    window._on_save()
                wait(lambda: not window.has_unsaved_changes)
                self.assertFalse(window.requires_save_as)
                self.assertTrue(destination.exists())
                self.assertEqual(SceneDocument(destination).hierarchy()[0]["path"], "/World")
                window.open_scene(str(destination))
                wait(lambda: window._ready and window.current_scene_path == str(destination))
                self.assertTrue(window.reconstruction_warning.isVisible())
            finally:
                window.has_unsaved_changes = False
                window.close()
                wait(lambda: not window.isVisible())
            self.assertFalse(draft_path.exists())
