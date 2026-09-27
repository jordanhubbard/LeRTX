import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.photo_ui import build_photo_dialog
from lertx.transport import ConnectionProbe
from lertx.ui import build_application
from tests.test_reconstruction import scene_payload


class PhotoUiTests(unittest.TestCase):
    def setUp(self):
        from PySide6.QtGui import QImage
        self.app = build_application([])
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"photo.png"
        image = QImage(100,100,QImage.Format.Format_RGB888)
        image.fill(0xff66aa)
        image.setText("private", "metadata-not-for-upload")
        self.assertTrue(image.save(str(self.path)))
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.reject()
            dialog.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def dialog(self, probe):
        dialog = build_photo_dialog(copy.deepcopy(DEFAULT_PROFILE), probe)
        self.dialogs.append(dialog)
        dialog.show()
        return dialog

    def wait(self, predicate):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        self.fail("Photo UI did not complete")

    def test_preview_is_explicit_and_strips_metadata(self):
        calls = []
        def tester(*args, **kwargs):
            calls.append(args)
            return {"state":"invalid_scene"}
        dialog = self.dialog(ConnectionProbe(tester))
        dialog.key_input.setText('test-only-key')
        dialog.select_photo(self.path)
        self.assertEqual(calls, [])
        self.assertIsNotNone(dialog.image_bytes)
        self.assertNotIn(b"metadata-not-for-upload", dialog.image_bytes)
        self.assertTrue(dialog.upload_button.isEnabled())
        dialog.upload_button.click()
        self.wait(lambda: "valid scene" in dialog.status.text())
        self.assertEqual(len(calls), 1)
        self.assertTrue(dialog.isVisible())

    def test_cancel_ignores_late_result_and_prevents_parallel_retry(self):
        started, release = threading.Event(), threading.Event()
        def tester(*args, **kwargs):
            started.set()
            release.wait(5)
            return {"state":"success", "scene_text":json.dumps(scene_payload())}
        probe = ConnectionProbe(tester)
        first = self.dialog(probe)
        first.key_input.setText('test-only-key')
        first.select_photo(self.path)
        first.upload()
        self.wait(started.is_set)
        first.reject()
        second = self.dialog(probe)
        second.key_input.setText('test-only-key')
        second.select_photo(self.path)
        try:
            second.upload()
            self.assertIn("still finishing", second.status.text())
            self.assertIsNone(first.result_scene)
            release.set()
            self.wait(lambda: probe._future.done())
            self.assertIsNone(first.result_scene)
        finally:
            release.set()

    def test_bad_image_never_enables_upload(self):
        dialog = self.dialog(ConnectionProbe())
        dialog.select_photo(Path(self.directory.name)/"missing.png")
        self.assertIsNone(dialog.image_bytes)
        self.assertFalse(dialog.upload_button.isEnabled())

    def test_missing_key_never_starts_request_then_inline_key_allows_success(self):
        calls=[]
        def tester(profile,image,**kwargs):
            calls.append((profile,image))
            return {'state':'success','scene_text':json.dumps(scene_payload())}
        dialog=self.dialog(ConnectionProbe(tester));dialog.select_photo(self.path)
        original=dialog.image_bytes
        dialog.upload_button.click()
        self.assertEqual(calls,[])
        self.assertIn('Nothing has been uploaded',dialog.status.text())
        dialog.key_input.setText('test-only-key');dialog.upload_button.click()
        self.wait(lambda:dialog.result_scene is not None)
        self.assertEqual(calls[0][0]['llm']['api_key'],'test-only-key')
        self.assertEqual(calls[0][1],original)
        self.assertEqual(dialog.key_input.text(),'')

    def test_auth_failure_keeps_photo_and_allows_key_correction(self):
        dialog=self.dialog(ConnectionProbe(lambda *a,**k:{'state':'auth_failure'}))
        dialog.select_photo(self.path);original=dialog.image_bytes
        dialog.key_input.setText('test-only-key');dialog.upload_button.click()
        self.wait(lambda:'Authentication failed' in dialog.status.text())
        self.assertEqual(dialog.image_bytes,original)
        self.assertTrue(dialog.key_input.isEnabled())
        self.assertTrue(dialog.upload_button.isEnabled())
        self.assertFalse(dialog.progress.isVisible())
