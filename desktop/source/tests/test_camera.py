import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from lertx.camera import CameraService, camera_identity


class Backend(QObject):
    frame=Signal(object)
    failed=Signal(str)
    devices_changed=Signal()
    def __init__(self):
        super().__init__();self.items=[dict(id='one',name='Camera',persistent=True)];self.started=[]
    def devices(self):return self.items
    def start(self,identity):self.started.append(identity)
    def stop(self):pass


class CameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.backend=Backend();self.now=10.
        self.service=CameraService(Path(self.directory.name)/'config.json',backend=self.backend,clock=lambda:self.now)
        self.addCleanup(self.service.close)

    def test_selection_requires_fresh_preview_and_restart_does_not_open_camera(self):
        with self.assertRaises(ValueError):self.service.use_camera('one')
        self.service.preview('one');self.backend.frame.emit(object());self.service.use_camera('one')
        backend=Backend();other=CameraService(Path(self.directory.name)/'config.json',backend=backend)
        try:
            self.assertEqual(other.selected_id,'one');self.assertFalse(other.enabled);self.assertEqual(backend.started,[])
        finally:other.close()
        self.now+=3;self.service.check_age();self.assertIsNone(self.service.image)
        with self.assertRaises(ValueError):self.service.use_camera('one')

    def test_unplug_stops_capture_and_never_selects_replacement(self):
        self.service.preview('one');self.backend.frame.emit(object());self.service.use_camera('one')
        self.backend.items=[dict(id='two',name='Camera',persistent=True)];self.backend.devices_changed.emit()
        self.assertFalse(self.service.enabled);self.assertIsNone(self.service.image)
        self.assertEqual(self.service.selected_id,'one');self.assertEqual(self.backend.started,['one'])

    def test_session_identity_is_not_remembered_and_is_cleared_on_unplug(self):
        self.backend.items=[dict(id='session:01',name='Camera',persistent=False)]
        self.service.preview('session:01');self.backend.frame.emit(object());self.service.use_camera('session:01')
        self.assertEqual(json.loads(self.service.path.read_text())['device_id'],'')
        self.backend.items=[];self.service.refresh();self.assertEqual(self.service.selected_id,'')

    def test_linux_identity_tracks_by_id_when_enumeration_changes(self):
        root=Path(self.directory.name);link=root/'usb-camera-video-index0'
        link.touch()
        for node in ('/dev/video0','/dev/video4'):
            def resolve(path,strict=False):return Path(node) if path==link else path
            with patch.object(Path,'resolve',resolve):
                self.assertEqual(camera_identity(node.encode(),'linux',root),('linux-by-id:'+link.name,True))
        self.assertEqual(camera_identity(b'/dev/video0','linux',root/'missing'),('session:'+b'/dev/video0'.hex(),False))
        self.assertEqual(camera_identity(b'windows-device-interface','win32'),(b'windows-device-interface'.hex(),True))

    def test_no_frames_reports_failure(self):
        self.service.preview('one');self.now+=9;self.service.check_age()
        self.assertFalse(self.service.enabled);self.assertIn('No frames',self.service.status)
