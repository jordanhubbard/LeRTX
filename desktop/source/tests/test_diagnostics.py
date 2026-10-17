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

    def test_control_identity_mutation_and_validation(self):
        from PySide6.QtWidgets import QPushButton, QLineEdit
        self.owner.show()
        button = QPushButton('Diagnostic test', self.owner)
        button.show()
        edit = QLineEdit(self.owner)
        edit.show()
        hits = []
        button.clicked.connect(lambda: hits.append(True))
        controls = self.call('/ui')[0]['widgets']
        key = next(c['id'] for c in controls if c.get('text') == 'Diagnostic test')
        self.assertEqual(key, self.service.control.identify(button))
        result = self.call('/command', {'command':'ui_action','id':key,'action':'click'})
        self.app.processEvents()
        self.assertEqual(hits, [True])
        self.assertTrue(any(e.get('operation') == result['operation'] and e['kind'] == 'control.completed'
                            for e in self.call('/events')))
        button.setEnabled(False)
        result = self.call('/command', {'command':'ui_action','id':key,'action':'click'})
        self.app.processEvents()
        self.assertTrue(any(e.get('operation') == result['operation'] and e['kind'] == 'control.failed'
                            for e in self.call('/events')))
        with self.assertRaises(ValueError):self.service.control.submit({'command':'ui_action','id':'stale','action':'click'})
        self.assertIn('open_hardware', self.call('/services'))
        with self.assertRaises(ValueError):self.service.control.submit({'command':'service','name':'eval'})
        with self.assertRaises(ValueError):self.service.control.submit({'command':'service','name':'open_hardware','role':'bad'})

    def test_control_modal_dialog_keeps_http_responsive(self):
        from PySide6.QtWidgets import QPushButton, QDialog, QVBoxLayout
        self.owner.show()
        button = QPushButton('Open test modal', self.owner)
        button.show()
        dialogs = []
        def open_dialog():
            dialog = QDialog(self.owner)
            dialog.setWindowTitle('Control modal')
            close = QPushButton('Finish test', dialog)
            QVBoxLayout(dialog).addWidget(close)
            close.clicked.connect(dialog.accept)
            dialogs.append(dialog)
            dialog.exec()
        button.clicked.connect(open_dialog)
        # A client thread operates both requests while Qt runs its nested loop.
        def client():
            controls = request(self.session, '/ui')
            key = next(c['id'] for w in controls for c in w['widgets'] if c.get('text') == 'Open test modal')
            result = request(self.session, '/command', {'command':'ui_action','id':key,'action':'click'})
            controls = request(self.session, '/ui')
            key = next(c['id'] for w in controls for c in w['widgets'] if c.get('text') == 'Finish test')
            request(self.session, '/command', {'command':'ui_action','id':key,'action':'click'})
            return result
        from PySide6.QtCore import QTimer
        from shiboken6 import isValid
        QTimer.singleShot(4000, lambda: [d.reject() for d in dialogs if isValid(d)])
        future = self.pool.submit(client)
        deadline = time.monotonic()+7
        while not future.done() and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(future.result(timeout=1)['queued'])

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
