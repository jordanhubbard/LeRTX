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
    def test_cached_controls_must_match_role_and_attachment(self):
        self.connect();p=self.panel;owner=self.owner
        owner._hardware_windows['follower']=p
        other=Candidate('different-port',1,2,'different-device')
        self.assertFalse(owner.open_hardware(other,'follower'))
        self.assertIn('assignment changed',owner.statusBar().currentMessage())
        self.assertIs(owner._hardware_windows['follower'],p)
        self.assertFalse(owner.open_hardware(p.session.candidate,'leader'))
        self.assertNotIn('leader',owner._hardware_windows)
        self.assertTrue(owner.open_hardware(p.session.candidate,'follower'))
        self.assertEqual(self.serial.writes,[])
    def test_back_to_devices_waits_for_session_shutdown(self):
        self.connect();returned=[]
        self.owner._on_devices=lambda:returned.append(self.panel.session.alive)
        self.panel.parent_button.click()
        self.wait(lambda:bool(returned))
        self.assertEqual(returned,[False])
        self.assertTrue(self.panel.shutdown_complete)

    def test_scene_load_keeps_registry_and_hardware_controls_available(self):
        from types import SimpleNamespace
        owner=self.owner;owner.worker=SimpleNamespace()
        owner._command=lambda *args,**kwargs:None
        owner._hardware_windows['follower']=self.panel
        for path in ('initial.usda','replacement.usda'):
            owner.open_scene(path)
            self.assertFalse(owner.devices.closing)
            self.assertTrue(self.panel.session.alive)
            self.assertTrue(owner.open_hardware(self.panel.session.candidate,'follower'))
            self.assertTrue(self.panel.isVisible())
        self.connect()
        self.assertEqual(self.panel.session.snapshot()['state'],'read-only')
        self.assertEqual(self.serial.writes,[])
        owner.worker=None

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
        self.panel.shutdown();self.wait(lambda:not self.panel.session.alive)
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
        self.assertTrue(self.panel.torque_button.isEnabled())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):self.panel.torque_button.click()
        self.wait(lambda:self.panel.session.snapshot()['state']=='armed');self.panel.poll()
        self.panel.targets['shoulder_pan'].setValue(10)
        self.panel.send_buttons['shoulder_pan'].click()
        self.wait(lambda:self.panel.session.snapshot()['targets'].get(1,0)>2100)
        self.panel.move_button.setDown(True);self.panel.poll()
        self.wait(lambda:self.panel.session.snapshot()['sample']['motors'][1]['position']>2050)
        self.panel.move_button.setDown(False);self.panel.poll()
        self.wait(lambda:self.panel.session.snapshot()['targets'][1]<2100)
        self.panel.torque_button.click()
        self.wait(lambda:self.panel.session.snapshot()['stop_confirmed'] is True)
        self.assertTrue(all(r[40]==0 for r in self.serial.registers.values()))
    def test_raw_readonly_without_calibration_and_close(self):
        self.panel.connect_button.click();self.wait(lambda:self.panel.session.snapshot()['state']=='read-only')
        self.panel.poll();self.assertFalse(self.panel.torque_button.isEnabled())
        self.assertIn('calibration',self.panel.motor_reason.text())
        self.assertIn('unavailable',self.panel.torque_button.text())
        self.assertEqual(self.panel.readings['shoulder_pan',1].text(),'2048')
        self.panel.close();self.wait(lambda:not self.panel.session.alive)
        self.assertEqual(self.serial.writes,[])
    def test_cancel_arm_dialog_does_not_write(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):self.panel.torque_button.click()
        self.panel.poll();self.assertEqual(self.serial.writes,[])
        self.assertIn('cancelled',self.panel.motor_result.text())

    def test_motor_feedback_confirms_enable_and_each_release(self):
        from PySide6.QtWidgets import QMessageBox
        p=self.panel;self.connect()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):p.torque_button.click()
        self.wait(lambda:'Enabled and verified' in p.motor_result.text())
        p.poll();self.assertIn('Release motors',p.torque_button.text())
        self.assertIn('ON · all 6',p.torque_status.text())
        p.torque_button.click()
        self.assertIn('Releasing',p.motor_result.text())
        self.wait(lambda:'Released and verified' in p.motor_result.text())
        p.poll();self.assertIn('Engage motors',p.torque_button.text())
        self.assertIn('OFF · all 6',p.torque_status.text())
        first=p.stop_request;p.release_torque()
        self.assertGreater(p.stop_request,first)
        self.assertIn('Releasing',p.motor_result.text())
        self.wait(lambda:'Released and verified' in p.motor_result.text())

    def test_disconnected_release_reports_no_confirmation(self):
        self.panel.release_torque()
        self.assertIn('no motor connection',self.panel.motor_result.text())
        self.assertEqual(self.serial.writes,[])

    def test_uncalibrated_mixed_torque_offers_release_not_engage(self):
        p=self.panel;self.serial.registers[1][40]=1
        p.connect_button.click();self.wait(lambda:p.session.snapshot()['state']=='read-only');p.poll()
        self.assertIn('1 of 6',p.torque_status.text())
        self.assertTrue(p.torque_button.isEnabled());self.assertIn('Release motors',p.torque_button.text())
        p.torque_button.click();self.wait(lambda:'Released and verified' in p.motor_result.text());p.poll()
        self.assertFalse(p.torque_button.isEnabled());self.assertIn('calibration',p.motor_reason.text())

    def test_old_stop_acknowledgement_cannot_confirm_new_release(self):
        self.connect();p=self.panel;p.timer.stop()
        snapshot=p.session.snapshot();snapshot['stop_confirmed']=True;snapshot['stop_completed']=1
        p.motor_action='stop';p.stop_request=2;p.motor_sequence=snapshot['sample']['sequence']-1
        p.motor_result.setText('Releasing motors…');p.update_motor_feedback(snapshot)
        self.assertEqual(p.motor_action,'stop');self.assertIn('Releasing',p.motor_result.text())

    def test_enable_error_is_visible_beside_controls(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect();self.serial.registers[1][9:11]=(513).to_bytes(2,'little')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):self.panel.torque_button.click()
        self.wait(lambda:'Enable failed:' in self.panel.motor_result.text())
        self.assertFalse(self.panel.torque_button.isEnabled())
        self.assertIn('fault',self.panel.motor_reason.text())

    def test_failed_stop_is_reported_before_panel_shutdown(self):
        from PySide6.QtWidgets import QMessageBox
        self.connect()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):self.panel.torque_button.click()
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
        low,high=owner.robot_panel._range['leader','shoulder_pan']
        owner.robot_panel.sliders['leader','shoulder_pan'].setValue(1000)
        self.assertEqual(owner.viewport_label.intent,('leader','shoulder_pan',high))
        owner.robot_panel.update_state({'positions':{'leader':home_positions('leader')},'following':True,'live_roles':['leader']})
        self.assertFalse(owner.robot_panel.sliders['leader','shoulder_pan'].isEnabled())
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

    def test_follower_unlock_survives_busy_worker(self):
        from types import SimpleNamespace
        from lertx.robot import home_positions
        owner=self.owner;owner._ready=True;panel=owner.robot_panel
        state={'positions':{'follower':home_positions('follower')},'following':True}
        panel.update_state(state)
        self.assertFalse(panel.sliders['follower','wrist_roll'].isEnabled())
        owner._pending=[object()]
        panel.follow.setChecked(False)
        self.assertEqual(panel.pending_follow,False)
        panel.update_state(state)
        self.assertFalse(panel.follow.isChecked())
        calls=[]
        def command(role,following):
            calls.append(following)
            return {**state,'following':following}
        owner.worker=SimpleNamespace(command_robot=command)
        owner._command=lambda fn,callback:callback(fn())
        owner._apply_status=panel.update_state
        owner._pending=[]
        try:
            panel.flush()
            self.assertEqual(calls,[False])
            self.assertTrue(panel.sliders['follower','wrist_roll'].isEnabled())
            low,high=panel._range['follower','wrist_roll']
            panel.sliders['follower','wrist_roll'].setValue(800)
            self.assertAlmostEqual(owner.viewport_label.intent[2],low+(high-low)*.8)
        finally:owner._ready=False;owner.worker=None;owner._pending=[]

    def test_live_view_queues_behind_renderer_and_cancels_superseded_work(self):
        from types import SimpleNamespace
        from lertx.joint_binding import JointBinding,RobotBinding
        from lertx.robot import JOINT_NAMES,joint_limits
        self.connect();p=self.panel;p.timer.stop();owner=self.owner;owner._frame_timer.stop()
        joints=[]
        for i,name in enumerate(JOINT_NAMES,1):
            low,high=joint_limits('follower')[name]
            joints.append(JointBinding(name,i,'percent' if name=='gripper' else 'degrees',
                (20.,80.) if name=='gripper' else (-10.,10.),(low+(high-low)*.4,low+(high-low)*.6)))
        p.binding=RobotBinding('follower',p.session.device_id,p.calibration.identity,tuple(joints))
        commands=[];frames=[]
        owner._ready=True;owner._pending=[object()]
        owner.worker=SimpleNamespace(hardware_pose=lambda *args:frames.append(args) or {},release_hardware=lambda role:{})
        owner._command=lambda fn,callback=None:commands.append((fn,callback))
        owner._accept_frame=lambda frame:None;owner._apply_status=lambda state:None
        try:
            p.live.setChecked(True);p.poll()
            self.assertEqual(len(commands),1)
            p.poll();self.assertEqual(len(commands),1)
            fn,callback=commands.pop(0);callback(fn())
            self.assertEqual(len(frames),1)
            p.sequence=-1;p.poll();p.live.setChecked(False)
            fn,callback=commands.pop(0);callback(fn())
            self.assertEqual(len(frames),1)
            self.assertEqual(self.serial.writes,[])
        finally:
            owner._ready=False;owner._pending=[];owner.worker=None
