"""Real Qt controls with the real SDK and an emulated serial bus."""
import copy
import json
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from lertx.devices import Candidate
from lertx.hardware import HardwareSession
from lertx.hardware_ui import build_hardware_panel
from lertx.usb_bus import FeetechBus
from lertx.ui import build_application,build_main_window
from lertx.config import DEFAULT_PROFILE
from tests.test_hardware import SerialRobot,calibration


class HardwareUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=build_application([])
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.owner=build_main_window(copy.deepcopy(DEFAULT_PROFILE),lambda:None,'unused.usda',str(Path(self.directory.name)/'settings.json'))
        self.serial=SerialRobot()
        def factory(candidate,role):
            return HardwareSession(candidate,role,verify=lambda c:None,
                bus_factory=lambda port:FeetechBus(port,serial_factory=lambda **kwargs:self.serial))
        self.panel=build_hardware_panel(self.owner,Candidate('fake-ui',1,2,'unique'),'follower',factory)
        self.panel.isActiveWindow=lambda:True
        self.addCleanup(self.cleanup)
    def wait(self,condition,seconds=2):
        from PySide6.QtTest import QTest
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            self.app.processEvents()
            if condition():return
            QTest.qWait(5)
        self.fail('Condition failed: '+repr(self.panel.session.snapshot()))
    def cleanup(self):
        self.panel.shutdown();self.wait(lambda:not self.panel.session._thread.is_alive())
        self.panel.deleteLater();self.owner.deleteLater();self.app.processEvents()
    def load_calibration(self):
        path=Path(self.directory.name)/'calibration.json';path.write_text(json.dumps(calibration().values))
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',return_value=(str(path),'')):
            self.panel.import_button.click()
    def connect(self):
        self.load_calibration();self.panel.connect_button.click()
        self.wait(lambda:self.panel.session.snapshot()['state']=='read-only')
        self.panel.poll()
    def test_connect_arm_held_move_release_and_stop_through_widgets(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect();self.assertEqual(self.serial.writes,[])
        self.assertTrue(self.panel.arm_button.isEnabled())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):self.panel.arm_button.click()
        self.wait(lambda:self.panel.session.snapshot()['state']=='armed');self.panel.poll()
        self.panel.targets['shoulder_pan'].setValue(10)
        self.panel.send_buttons['shoulder_pan'].click()
        self.wait(lambda:self.panel.session.snapshot()['targets'].get(1,0)>2100)
        self.panel.move_button.setDown(True);self.panel.poll()
        self.wait(lambda:self.panel.session.snapshot()['sample']['motors'][1]['position']>2050)
        self.panel.move_button.setDown(False);self.panel.poll()
        self.wait(lambda:self.panel.session.snapshot()['targets'][1]<2100)
        self.panel.stop_button.click()
        self.wait(lambda:self.panel.session.snapshot()['stop_confirmed'] is True)
        self.assertTrue(all(r[40]==0 for r in self.serial.registers.values()))
    def test_raw_readonly_without_calibration_and_close(self):
        self.panel.connect_button.click();self.wait(lambda:self.panel.session.snapshot()['state']=='read-only')
        self.panel.poll();self.assertFalse(self.panel.arm_button.isEnabled())
        self.assertEqual(self.panel.readings['shoulder_pan',1].text(),'2048')
        self.panel.close();self.wait(lambda:not self.panel.session._thread.is_alive())
        self.assertEqual(self.serial.writes,[])
    def test_cancel_arm_dialog_does_not_write(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):self.panel.arm_button.click()
        self.panel.poll();self.assertEqual(self.serial.writes,[])

    def test_failed_stop_is_reported_before_panel_shutdown(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):self.panel.arm_button.click()
        self.wait(lambda:self.panel.session.snapshot()['state']=='armed')
        self.serial.drop=True
        with patch.object(QMessageBox,'critical',return_value=QMessageBox.StandardButton.Ok) as message:
            self.panel.shutdown();self.wait(lambda:self.panel.shutdown_complete)
            self.assertTrue(message.called)
            self.assertIn('power switch',message.call_args.args[2])
    def test_selected_joint_slider_produces_bounded_simulation_intent(self):
        from lertx.robot import home_positions
        owner=self.owner;owner._ready=True
        owner.robot_panel.update_state({'positions':{'leader':home_positions('leader')},'following':True})
        owner.robot_panel.select_joint({'joint':dict(role='leader',name='shoulder_pan',low=-1.,high=1.,value=0.,locked=False)})
        owner.robot_panel.joint_slider.setValue(1000)
        self.assertEqual(owner.viewport_label.intent,('leader','shoulder_pan',1.))
        owner.robot_panel.update_state({'positions':{'leader':home_positions('leader')},'following':True,'live_roles':['leader']})
        self.assertFalse(owner.robot_panel.joint_slider.isEnabled())
        owner._ready=False

    def test_native_failure_turns_off_live_view_without_motor_writes(self):
        from types import SimpleNamespace
        from lertx.joint_binding import JointBinding,RobotBinding
        from lertx.robot import JOINT_NAMES,joint_limits
        self.connect();joints=[]
        for i,name in enumerate(JOINT_NAMES,1):
            low,high=joint_limits('follower')[name]
            joints.append(JointBinding(name,i,'percent' if name=='gripper' else 'degrees',
                (20.,80.) if name=='gripper' else (-10.,10.),
                (low+(high-low)*.4,low+(high-low)*.6)))
        self.panel.binding=RobotBinding('follower',self.panel.session.device_id,self.panel.calibration.identity,tuple(joints))
        def fail(*args):raise ValueError('Observation expired in renderer queue')
        owner=self.owner;owner._ready=True
        owner.worker=SimpleNamespace(hardware_pose=fail,release_hardware=lambda role:{})
        owner._apply_status=lambda status:None
        owner._command=lambda fn,callback=None:callback(fn()) if callback else fn()
        try:
            self.panel.live.setChecked(True);self.panel.poll()
            self.assertFalse(self.panel.live.isChecked())
            self.assertIn('expired',self.panel.message.text())
            self.assertEqual(self.serial.writes,[])
        finally:owner._ready=False;owner.worker=None
