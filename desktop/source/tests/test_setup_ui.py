"""Operator flow through real Qt widgets and pinned SDK byte-stream emulator."""
import copy,json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from lertx.config import DEFAULT_PROFILE
from lertx.devices import Candidate
from lertx.hardware import HardwareSession
from lertx.setup_ui import build_setup_wizard
from lertx.transport import ConnectionProbe
from lertx.ui import build_application,build_main_window
from lertx.usb_bus import FeetechBus
from tests.test_setup import CalibrationSerial

class SetupUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=build_application([])
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.owner=build_main_window(copy.deepcopy(DEFAULT_PROFILE),lambda:None,'unused.usda',str(Path(self.directory.name)/'settings.json'))
        self.owner._frame_timer.stop();self.owner._ready=True
        self.frames=[]
        self.owner.worker=SimpleNamespace(setup_pose=lambda *args:self.frames.append(args) or {},release_hardware=lambda role:{})
        self.owner._command=lambda fn,callback=None:callback(fn()) if callback else fn()
        self.owner._accept_frame=lambda frame:None;self.owner._apply_status=lambda state:None
        self.serial=CalibrationSerial()
        def factory(candidate,role):
            return HardwareSession(candidate,role,verify=lambda c:None,bus_factory=lambda p:FeetechBus(p,serial_factory=lambda **k:self.serial))
        self.wizard=build_setup_wizard(self.owner,factory,ConnectionProbe(lambda **k:{'state':'success','candidates':[Candidate('setup-test',1,2,'unique')]}))
        self.wizard.show();self.addCleanup(self.cleanup)
        self.wait(lambda:bool(self.wizard.candidates))
    def wait(self,predicate):
        from PySide6.QtTest import QTest
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            self.app.processEvents()
            if predicate():return
            QTest.qWait(5)
        self.fail('Wizard did not advance: '+self.wizard.status.text())
    def cleanup(self):
        w=self.wizard
        if w.transferred:
            for p in self.owner._hardware_windows.values():p.shutdown();p.session._thread.join(3)
        else:
            w.shutdown()
            if w.session:self.wait(lambda:not w.session._thread.is_alive())
        w.timer.stop();self.owner._ready=False;self.owner.worker=None
        w.deleteLater();self.owner.deleteLater();self.app.processEvents()
    def begin(self):
        w=self.wizard;w.next_button.click()
        self.wait(lambda:w.session.snapshot()['state']=='read-only' and not w.pending)
        self.assertEqual(self.serial.writes,[])
        w.support.setChecked(True);w.advance();self.assertEqual(w.step,2)
        self.wait(lambda:bool(self.frames));self.assertIsNone(self.frames[-1][2])
        w.reference_check.setChecked(True);w.advance()
        self.wait(lambda:w.step==3)
    def test_role_identity_remains_visible_through_joint_steps(self):
        w=self.wizard;w.role_box.setCurrentText('leader')
        self.assertEqual(w.role,'leader')
        self.assertIn('Leader',w.identity.text())
        self.assertIn('#1FAD9E',w.identity.styleSheet())
        self.begin()
        self.assertFalse(w.role_box.isVisible())
        self.assertTrue(w.identity.isVisible())
        self.assertIn('Leader',w.preview_window.identity.text())
        self.assertIn('Leader (selected)',w.preview_window.legend.text())
        self.assertEqual(w.joint_map.role_color,'#1FAD9E')
    def test_custom_color_updates_identity_and_cannot_change_connected_arm(self):
        from lertx.config import save_profile,load_profile
        calls=[]
        def configure(profile,path):
            calls.append(profile);save_profile(profile,path);return {}
        self.owner.worker.configure=configure
        self.owner._hardware_windows['closed']=SimpleNamespace(session=SimpleNamespace(_thread=SimpleNamespace(is_alive=lambda:False)))
        w=self.wizard;w.apply_color('#123456')
        del self.owner._hardware_windows['closed']
        self.assertIn('#123456',w.identity.styleSheet())
        self.assertEqual(self.owner.arm_swatches['follower'].pixmap().toImage().pixelColor(8,8).name(),'#123456')
        self.assertEqual(load_profile(self.owner.config_path)['general']['follower_color'],'#123456')
        w.advance();w.apply_color('#ffffff')
        self.assertEqual(len(calls),1)
    def test_full_calibration_exports_and_mirrors_each_joint_without_torque(self):
        w=self.wizard;self.begin()
        for i in range(1,7):
            self.wait(lambda:w.sweep.start is not None)
            self.serial.registers[i][56:58]=(1600).to_bytes(2,'little')
            self.wait(lambda:w.sweep.phase==1)
            self.serial.registers[i][56:58]=(2500).to_bytes(2,'little')
            self.wait(lambda:w.sweep.phase==2)
            self.serial.registers[i][56:58]=(1600).to_bytes(2,'little')
            self.wait(lambda:w.step==i+3)
        self.assertEqual(w.step,9)
        w.advance();self.assertEqual(w.step,9,'Final hardware save still requires review')
        w.confirm.setChecked(True);w.advance();self.wait(lambda:w.step==10)
        self.assertTrue((w.run_dir/'original-registers.json').is_file())
        saved=json.loads((w.run_dir/'calibration.json').read_text());self.assertEqual(len(saved),6)
        self.assertTrue((w.run_dir/'binding.json').is_file())
        self.assertTrue(any(f[2] is not None for f in self.frames))
        self.assertFalse(any(a==40 and value for _,a,value,_ in self.serial.writes))
        self.assertEqual(w.session.snapshot()['state'],'read-only')
    def test_cancel_restores_and_closes_without_enabling_motors(self):
        self.begin();self.wizard.close()
        self.wait(lambda:self.wizard.shutdown_complete)
        self.assertEqual(int.from_bytes(self.serial.registers[1][9:11],'little'),512)
        self.assertTrue(self.serial.closed)
    def test_joint_cannot_be_skipped_before_sweep_completion(self):
        self.begin();w=self.wizard
        w.advance();self.assertEqual(w.step,3)
        w.confirm.setChecked(True);w.advance();self.assertEqual(w.step,3)
        self.assertIn('comfortable end',w.status.text())
    def test_named_joint_slider_sets_intent_even_while_worker_busy(self):
        from lertx.robot import home_positions
        p=self.owner.robot_panel;p.update_state({'positions':{'leader':home_positions('leader')},'following':True})
        self.owner._pending=[object()]
        low,high=p._range['leader','shoulder_lift']
        p.sliders['leader','shoulder_lift'].setValue(1000)
        self.assertEqual(self.owner.viewport_label.intent,('leader','shoulder_lift',high))
        self.owner._pending=[]

    def test_busy_renderer_queues_one_preview_and_uses_latest_sample(self):
        self.begin();w=self.wizard;w.timer.stop();w.sequence=-1
        commands=[];self.owner._pending=[object()]
        self.owner._command=lambda fn,callback=None:commands.append((fn,callback))
        w.poll()
        self.assertEqual(len(commands),1,'Busy rendering must not starve telemetry')
        for _ in range(5):w.poll()
        self.assertEqual(len(commands),1,'Do not build an unbounded preview queue')
        self.serial.registers[1][56:58]=(2250).to_bytes(2,'little')
        self.wait(lambda:w.session.snapshot()['sample']['motors'][1]['position']==2250)
        fn,callback=commands.pop(0);callback(fn())
        self.assertAlmostEqual(self.frames[-1][1]['shoulder_pan'],(2250-2047)*2*3.141592653589793/4095)
        self.assertEqual(w.preview_step,3)
        self.owner._pending=[]

    def test_cancelled_preview_cannot_publish_after_live_view_disabled(self):
        self.begin();w=self.wizard;w.timer.stop();w.sequence=-1;commands=[]
        self.owner._command=lambda fn,callback=None:commands.append((fn,callback))
        w.poll();count=len(self.frames);w.live.setChecked(False)
        fn,callback=commands[0];callback(fn())
        self.assertEqual(len(self.frames),count)
        self.assertIsNone(w.preview_step)

    def test_stale_queued_sample_is_not_rendered(self):
        self.begin();w=self.wizard;w.timer.stop();w.sequence=-1;commands=[]
        self.owner._command=lambda fn,callback=None:commands.append((fn,callback))
        w.poll();count=len(self.frames)
        original=w.session.snapshot
        w.session.snapshot=lambda:{**original(),'stale':True}
        fn,callback=commands[0];callback(fn())
        self.assertEqual(len(self.frames),count)
        self.assertIn('stale',w.preview_status.text())
        self.assertIsNone(w.preview_step)
        w.session.snapshot=original

    def test_other_joint_motion_is_tolerated_and_does_not_advance(self):
        self.begin();w=self.wizard
        self.serial.registers[3][56:58]=(2250).to_bytes(2,'little')
        self.wait(lambda:w.session.snapshot()['sample']['motors'][3]['position']==2250)
        w.poll()
        self.assertEqual(w.joint_map.active,'shoulder_pan')
        self.assertNotIn('You are moving',w.movement.text())
        self.assertEqual(w.sweep.phase,0)
        self.assertEqual(w.step,3)
        self.assertIn('rotating platform',w.instructions.text())
        self.assertTrue(w.native_view.isVisible())
        self.assertTrue(w.preview_window.isWindow())
        self.assertFalse(w.joint_map.isVisible())

    def test_preview_window_receives_each_native_frame_and_reopens(self):
        from PySide6.QtGui import QImage
        w=self.wizard
        first=QImage(20,20,QImage.Format.Format_RGB888);first.fill(0xff0000)
        second=QImage(20,20,QImage.Format.Format_RGB888);second.fill(0x00ff00)
        self.owner.native_frame_ready.emit(first)
        self.assertEqual(w.native_view.image,first)
        self.owner.native_frame_ready.emit(second)
        self.assertEqual(w.native_view.image,second)
        w.preview_window.close();self.assertFalse(w.preview_window.isVisible())
        w.show_preview_button.click();self.assertTrue(w.preview_window.isVisible())

    def test_completed_sweep_waits_for_visible_current_rtx_preview(self):
        self.begin();w=self.wizard
        self.wait(lambda:w.sweep.start is not None)
        w.preview_window.close()
        for value,phase in ((1600,1),(2500,2),(1600,3)):
            self.serial.registers[1][56:58]=value.to_bytes(2,'little')
            self.wait(lambda:w.sweep.phase==phase)
        self.assertEqual(w.step,3)
        self.assertFalse(w.preview_is_current())
        w.open_preview()
        self.wait(lambda:w.step==4)

    def test_finish_transfers_live_window_and_shutdown_disposes_it(self):
        self.begin();w=self.wizard
        for name in w.capture.ranges:
            w.capture.ranges[name]=[1600,2500];w.capture.confirm(name)
        w.session.request('setup_save',w.capture.calibration())
        self.wait(lambda:w.session.snapshot()['setup']['state']=='saved')
        w.finish_setup()
        panel=self.owner._hardware_windows['follower']
        self.assertIs(panel.preview_window,w.preview_window)
        self.assertTrue(panel.preview_window.isVisible())
        panel.shutdown()
        self.assertTrue(panel.preview_window.disposed)

    def test_pending_save_blocks_back_and_duplicate_submission(self):
        self.begin();w=self.wizard;w.step=9;w.pending=True
        w.go_back();w.advance()
        self.assertEqual(w.step,9)
