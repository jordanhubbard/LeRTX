import copy
import concurrent.futures
import json
from pathlib import Path
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from lertx.config import DEFAULT_PROFILE
from lertx.debug_client import request
from lertx.live_debug import Diagnostics
from lertx.ui import build_application, build_main_window


class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = build_application([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.owner = build_main_window(copy.deepcopy(DEFAULT_PROFILE), lambda: None,
            'unused.usda', str(Path(self.directory.name)/'settings.json'))
        self.owner._frame_timer.stop()
        self.service = Diagnostics(self.owner)
        self.session = json.loads(self.service.path.read_text())
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def tearDown(self):
        self.service.close()
        self.assertFalse(self.service.path.exists())
        self.pool.shutdown()
        self.owner.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def call(self, path='/state', payload=None):
        future = self.pool.submit(request, self.session, path, payload)
        deadline = time.monotonic()+7
        while not future.done() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        return future.result(timeout=1)

    def test_observe_tune_and_capture_without_hardware(self):
        from PySide6.QtGui import QImage
        self.owner._image = QImage(16, 16, QImage.Format.Format_RGB32)
        self.owner._image.fill(0xff55aacc)
        state = self.call()
        self.assertEqual(state['devices'], [])
        self.assertEqual(state['schema'], 1)
        self.assertEqual(self.call('/command', {'command':'target_fps','value':15})['applied'], 15)
        self.assertEqual(self.call()['target_fps'], 15)
        self.assertEqual(self.owner.profile['rendering']['target_fps'], DEFAULT_PROFILE['rendering']['target_fps'])
        self.assertTrue(self.call('/frame').startswith(b'\x89PNG'))
        self.assertEqual([e for e in self.call('/events') if e['kind'].startswith('tuning.')][-1]['kind'], 'tuning.target_fps')

    def test_rejects_unauthenticated_browser_and_unsafe_commands(self):
        for headers in ({}, {'Authorization':'Bearer '+self.session['token'], 'Origin':'http://example.com'}):
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(urllib.request.Request(self.session['url']+'/state', headers=headers),timeout=2)
            self.assertEqual(context.exception.code, 403)
            context.exception.close()
        for command in ({'command':'arm'}, {'command':'eval','code':'1'},
                        {'command':'target_fps','value':0}, {'command':'target_fps','value':True},
                        {'command':'target_fps','value':20,'extra':1}):
            with self.assertRaises(ValueError):
                self.call('/command', command)
        self.assertFalse(self.owner.devices.alive)

    def test_owned_dialog_capture_includes_window_and_setup_state(self):
        from PySide6.QtWidgets import QDialog
        dialog = QDialog(self.owner)
        dialog.setWindowTitle('Covered application dialog')
        dialog.show()
        self.app.processEvents()
        windows = self.call()['windows']
        entry = next(w for w in windows if w['title'] == dialog.windowTitle())
        self.assertTrue(self.call('/window/'+entry['id']).startswith(b'\x89PNG'))
        self.assertTrue(any(w['title']==dialog.windowTitle() for w in self.call('/ui')))
        dialog.close()
        dialog.deleteLater()

    def test_bounded_events(self):
        for i in range(2000):self.service.record('sample', value=i)
        events = self.call('/events')
        self.assertEqual(len(events), 1200)
        self.assertEqual([e for e in events if e['kind']=='sample'][-1]['value'], 1999)
