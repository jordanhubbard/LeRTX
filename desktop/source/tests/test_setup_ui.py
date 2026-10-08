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
    def test_full_calibration_exports_and_mirrors_each_joint_without_torque(self):
        w=self.wizard;self.begin()
        for i in range(1,7):
            self.serial.registers[i][56:58]=(1800).to_bytes(2,'little')
            self.wait(lambda:w.capture.ranges[list(w.capture.ranges)[i-1]][0]==1800)
            self.serial.registers[i][56:58]=(2300).to_bytes(2,'little')
            self.wait(lambda:w.capture.ranges[list(w.capture.ranges)[i-1]][1]==2300)
            w.confirm.setChecked(True);w.advance()
        self.assertEqual(w.step,9);w.advance();self.wait(lambda:w.step==10)
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
    def test_reference_and_movement_require_operator_confirmation(self):
        self.begin();w=self.wizard
        w.advance();self.assertEqual(w.step,3)
        w.confirm.setChecked(True);w.advance();self.assertEqual(w.step,3)
        self.assertIn('100 encoder ticks',w.status.text())
    def test_named_joint_slider_sets_intent_even_while_worker_busy(self):
        from lertx.robot import home_positions
        p=self.owner.robot_panel;p.update_state({'positions':{'leader':home_positions('leader')},'following':True})
        self.owner._pending=[object()]
        low,high=p._range['leader','shoulder_lift']
        p.sliders['leader','shoulder_lift'].setValue(1000)
        self.assertEqual(self.owner.viewport_label.intent,('leader','shoulder_lift',high))
        self.owner._pending=[]
