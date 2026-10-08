import copy
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from concurrent.futures import Future

from lertx.config import DEFAULT_PROFILE
from lertx.transport import ConnectionProbe
from lertx.ui import build_application, build_main_window


class SettingsUiTests(unittest.TestCase):
    def setUp(self):
        self.app = build_application([])
        self.directory = tempfile.TemporaryDirectory()
        self.profile = copy.deepcopy(DEFAULT_PROFILE)
        self.profile["llm"].update(api_key="test-only-key", model="custom-model")
        self.window = build_main_window(self.profile, lambda: None, "", self.directory.name+"/settings.json")
        self.dialog = self.window.create_settings_dialog()
        self.dialog.show()

    def tearDown(self):
        self.dialog.reject()
        self.window._frame_timer.stop()
        self.window.deleteLater()
        # processEvents alone does not drain DeferredDelete without an exec loop.
        # Dispose previous dialogs/timers before the next responsiveness check.
        from PySide6.QtCore import QCoreApplication,QEvent
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.directory.cleanup()

    def test_defaults_stay_staged_and_cancel_preserves_profile(self):
        self.dialog._on_restore_defaults()
        self.assertTrue(self.dialog.isVisible())
        self.assertEqual(self.dialog._key_edit.text(), "")
        self.assertIsNone(self.dialog.result_profile())
        self.dialog.reject()
        self.assertEqual(self.window.profile["llm"]["model"], "custom-model")
        self.assertEqual(self.window.profile["llm"]["api_key"], "test-only-key")

    def test_fresh_intelligence_panel_keeps_key_blank_without_file_reads(self):
        from pathlib import Path
        fresh = build_main_window(copy.deepcopy(DEFAULT_PROFILE), lambda: None,
                                  "unused.usda", self.directory.name+"/fresh.json")
        try:
            with patch.dict("os.environ", {"OPENAI_API_KEY":"environment-key-must-not-load",
                                            "NVIDIA_API_KEY":"environment-key-must-not-load"}), \
                    patch("builtins.open", side_effect=AssertionError("Unexpected file read")), \
                    patch.object(Path, "open", side_effect=AssertionError("Unexpected Path read")):
                dialog = fresh.create_settings_dialog()
                self.assertEqual(dialog._key_edit.text(), "")
                self.assertEqual(dialog._collect_profile()["llm"]["api_key"], "")
                self.assertFalse(dialog._collect_profile()["llm"]["remember_key"])
                dialog.reject()
                dialog.deleteLater()
            self.assertEqual(fresh.profile["llm"]["api_key"], "")
        finally:
            fresh._frame_timer.stop()
            fresh.deleteLater()

    def test_ui_profile_commits_only_after_successful_worker_result(self):
        from PySide6.QtWidgets import QDialog
        from types import SimpleNamespace
        future = Future()
        self.window._frame_timer.stop()
        self.window._last_frame_at = float("inf")
        self.window.worker = SimpleNamespace(submit=lambda operation: future, _stop_event=threading.Event())
        candidate = copy.deepcopy(self.profile)
        candidate["general"]["theme"] = "light"
        with patch.object(self.window, "create_settings_dialog", return_value=self.dialog), \
                patch.object(self.dialog, "exec", return_value=QDialog.DialogCode.Accepted), \
                patch.object(self.dialog, "result_profile", return_value=candidate), \
                patch("lertx.config.save_profile") as save:
            self.window._on_open_settings()
            self.assertEqual(self.window.profile, self.profile)
            save.assert_not_called()
            future.set_result(({"path":"scene.usda", "dirty":True, "playing":False,
                               "time":0, "physics_error":"", "hierarchy":[]},
                               time.perf_counter(), time.perf_counter()))
            self.window._on_tick()
            self.assertEqual(self.window.profile, candidate)
            self.assertTrue(self.window.has_unsaved_changes)
        self.window.worker = None

    def test_failed_settings_apply_preserves_ui_profile_and_dirty_state(self):
        from PySide6.QtWidgets import QDialog
        from types import SimpleNamespace
        future = Future()
        self.window._frame_timer.stop()
        self.window.worker = SimpleNamespace(submit=lambda operation: future, _stop_event=threading.Event())
        self.window.has_unsaved_changes = True
        candidate = copy.deepcopy(self.profile)
        candidate["general"]["theme"] = "light"
        with patch.object(self.window, "create_settings_dialog", return_value=self.dialog), \
                patch.object(self.dialog, "exec", return_value=QDialog.DialogCode.Accepted), \
                patch.object(self.dialog, "result_profile", return_value=candidate):
            self.window._on_open_settings()
            future.set_exception(ValueError("Settings were not saved"))
            self.window._on_tick()
            self.assertEqual(self.window.profile, self.profile)
            self.assertTrue(self.window.has_unsaved_changes)
            self.assertIn("not saved", self.window.statusBar().currentMessage())
        self.window.worker = None

    def test_invalid_save_keeps_dialog_and_prior_profile(self):
        self.dialog._fields["llm.endpoint"].setText("http://invalid.example")
        self.dialog._on_save()
        self.assertTrue(self.dialog.isVisible())
        self.assertIn("llm.endpoint", self.dialog._validation_label.text())
        self.assertIsNone(self.dialog.result_profile())

    def test_malformed_endpoint_reports_field_error_without_throwing(self):
        self.dialog._fields["llm.endpoint"].setText("https://[broken")
        self.dialog._on_save()
        self.assertTrue(self.dialog.isVisible())
        self.assertIn("llm.endpoint", self.dialog._validation_label.text())
        self.assertIsNone(self.dialog.result_profile())

    def test_display_units_change_conversion_not_scene_scale(self):
        self.window._scene_units = .01
        for units, expected in (("m", .01), ("cm", 1.), ("mm", 10.)):
            self.window.profile["general"]["display_units"] = units
            self.assertEqual(self.window._display_factor(), expected)
            self.assertEqual(self.window._scene_units, .01)
        self.window.profile["general"]["theme"] = "light"
        self.window._apply_theme()
        self.assertIn("#f1f4f5", self.window.styleSheet())

    def test_unsaved_cancel_discard_and_failed_save(self):
        from PySide6.QtWidgets import QMessageBox
        self.window.has_unsaved_changes = True
        actions = []
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window._after_discard_confirmation(lambda: actions.append("cancelled"))
        self.assertEqual(actions, [])
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            self.window._after_discard_confirmation(lambda: actions.append("discarded"))
        self.assertEqual(actions, ["discarded"])
        class FailingSaveWorker:
            _stop_event = threading.Event()
            def submit(self, command):
                future = Future()
                future.set_exception(OSError("Save failed"))
                return future
        self.window.worker = FailingSaveWorker()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
            self.window._after_discard_confirmation(lambda: actions.append("saved"))
        self.window._on_tick()
        self.assertTrue(self.window.has_unsaved_changes)
        self.assertEqual(actions, ["discarded"])
        self.assertIn("Save failed", self.window.native_status_label.text())
        self.window.worker = None

    def test_untitled_save_cancel_does_not_clear_dirty(self):
        from PySide6.QtWidgets import QFileDialog
        self.window.requires_save_as = True
        self.window.has_unsaved_changes = True
        with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
            self.window._on_save()
        self.assertTrue(self.window.requires_save_as)
        self.assertTrue(self.window.has_unsaved_changes)
        self.assertEqual(self.window._pending, [])

    def test_untitled_save_rejects_temporary_descendants(self):
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        self.window.current_scene_path = str(Path(self.directory.name) / "untitled.usda")
        self.window.requires_save_as = True
        self.window.has_unsaved_changes = True
        destination = str(Path(self.directory.name) / "nested" / "saved.usda")
        with patch.object(QFileDialog, "getSaveFileName", return_value=(destination, "")):
            self.window._on_save()
        self.assertTrue(self.window.requires_save_as)
        self.assertTrue(self.window.has_unsaved_changes)
        self.assertEqual(self.window._pending, [])
        self.assertIn("outside the temporary workspace", self.window.native_status_label.text())

    def test_open_existing_scene_clears_untitled_only_after_success(self):
        self.window.requires_save_as = True
        self.window.current_scene_path = self.directory.name + "/untitled.usda"
        self.window.worker = object()
        callbacks = []
        with patch.object(self.window, "_command", side_effect=lambda operation, callback: callbacks.append(callback)), \
                patch.object(self.window, "_apply_status") as apply_status:
            self.window.open_scene(self.directory.name + "/existing.usda")
            self.assertTrue(self.window.requires_save_as)
            status = {"path": self.directory.name + "/existing.usda"}
            callbacks[0](status)
            self.assertFalse(self.window.requires_save_as)
            apply_status.assert_called_once_with(status)
        self.window.worker = None

    def test_test_connection_responsive_and_endpoint_change_invalidates(self):
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtCore import QTimer
        release = threading.Event()
        def tester(*args, cancel_token):
            release.wait(2)
            return {"state": "success"}
        self.dialog._probe = ConnectionProbe(tester)
        button = next(b for b in self.dialog.findChildren(QPushButton) if b.text() == "Test connection")
        beats = []
        timer = QTimer()
        timer.timeout.connect(lambda: beats.append(True))
        timer.start(5)
        try:
            button.click()
            self.assertEqual(self.dialog._connection_status.text(), "Testing...")
            deadline = time.monotonic()+1
            while len(beats) < 3 and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.005)
            self.assertGreater(len(beats), 2)
            endpoint = self.dialog._fields["llm.endpoint"]
            endpoint.setText("https://changed.example/v1/responses")
            endpoint.textEdited.emit(endpoint.text())
            self.assertEqual(self.dialog._key_edit.text(), "")
            release.set()
            deadline = time.monotonic()+.1
            while time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.005)
            self.assertEqual(self.dialog._connection_status.text(), "")
        finally:
            release.set()
            timer.stop()


class ProviderPresetTests(unittest.TestCase):
    def setUp(self):
        self.app = build_application([])
        self.directory = tempfile.TemporaryDirectory()
        self.profile = copy.deepcopy(DEFAULT_PROFILE)
        self.window = build_main_window(self.profile, lambda: None, "", self.directory.name+"/settings.json")
        self.dialog = self.window.create_settings_dialog()
        self.dialog.show()

    def tearDown(self):
        self.dialog.reject()
        self.window._frame_timer.stop()
        self.window.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_default_profile_shows_nvidia_preset_selected(self):
        self.assertEqual(self.dialog._provider_combo.currentText(), "NVIDIA")

    def test_selecting_a_preset_fills_endpoint_and_model_and_clears_key(self):
        self.dialog._key_edit.setText("some-key")
        self.dialog._provider_combo.setCurrentText("OpenRouter")
        endpoint, model = self.dialog.PROVIDER_PRESETS["OpenRouter"]
        self.assertEqual(self.dialog._fields["llm.endpoint"].text(), endpoint)
        self.assertEqual(self.dialog._fields["llm.model"].text(), model)
        self.assertEqual(self.dialog._key_edit.text(), "")

    def test_editing_endpoint_away_from_a_preset_switches_to_custom(self):
        endpoint = self.dialog._fields["llm.endpoint"]
        endpoint.setText("https://my-own-gateway.example/v1/responses")
        endpoint.textEdited.emit(endpoint.text())
        self.assertEqual(self.dialog._provider_combo.currentText(), "Custom")

    def test_restore_defaults_resyncs_provider_combo_to_nvidia(self):
        from PySide6.QtWidgets import QDialogButtonBox
        self.dialog._provider_combo.setCurrentText("OpenAI")
        buttons = self.dialog.findChild(QDialogButtonBox)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).click()
        self.assertEqual(self.dialog._provider_combo.currentText(), "NVIDIA")
