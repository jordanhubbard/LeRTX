import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from lertx.config import DEFAULT_PROFILE
from lertx.ui import build_application,build_main_window
from lertx.robot_session_ui import build_robot_session_panel
from lertx.devices_ui import build_devices_dialog
from lertx.devices import Candidate
from lertx.transport import ConnectionProbe


class SessionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=build_application([])

    def test_paused_preset_previews_apply_actual_poses_without_connecting_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            owner=build_main_window(copy.deepcopy(DEFAULT_PROFILE),lambda:None,'unused',str(Path(directory)/'settings.json'))
            owner._frame_timer.stop();owner._ready=True;calls=[]
            owner.worker=SimpleNamespace(setup_pose=lambda role,values:calls.append((role,values)) or {},
                release_hardware=lambda role:{},tick=lambda dt:{})
            owner._command=lambda fn,callback=None:callback(fn()) if callback else fn()
            owner._accept_frame=lambda result:None
            panel=build_robot_session_panel(owner)
            try:
                panel.preview_pose()
                self.assertEqual({r for r,v in calls},{'leader','follower'})
                self.assertFalse(panel.preview_pending);self.assertEqual(panel.preview.mode,'simulation')
                self.assertFalse(owner.devices.active_controllers())
                self.assertFalse(panel.live.isChecked())
            finally:
                panel.close();owner.camera_service.close();owner.devices.shutdown();owner.worker=None;owner.deleteLater()
                self.app.processEvents()

    def test_device_manager_transfers_session_only_assignments_explicitly(self):
        from PySide6.QtWidgets import QWidget
        with tempfile.TemporaryDirectory() as directory:
            parent=QWidget();parent.profile=copy.deepcopy(DEFAULT_PROFILE);received=[]
            parent.open_robot_session=lambda **kw:received.append(kw) or True
            dialog=build_devices_dialog(parent.profile,ConnectionProbe(lambda **kw:dict(state='success',candidates=[])),Path(directory)/'devices.json',parent)
            candidate=Candidate('/dev/ttyUSB0',1,2,None)
            dialog.roles.assign('leader',candidate,[candidate]);dialog.open_session()
            self.assertEqual(received,[dict(session_assignments={'leader':candidate.attachment})])
            self.assertFalse(dialog.roles.session)
            dialog.deleteLater();parent.deleteLater();self.app.processEvents()
