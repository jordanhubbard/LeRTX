import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from lertx.device_control import DeviceRegistry
from lertx.devices import Candidate
from lertx.hardware import HardwareSession
from lertx.joint_binding import RobotBinding,JointBinding
from lertx.robot import JOINT_NAMES,joint_limits
from lertx.robot_session import RobotSession,load_recording,validate_recording
from lertx.usb_bus import FeetechBus
from tests.test_hardware import SerialRobot,calibration


class RobotSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.serials={r:SerialRobot() for r in ('leader','follower')}
        def factory(candidate,role):
            return HardwareSession(candidate,role,verify=lambda c:None,
                bus_factory=lambda p:FeetechBus(p,serial_factory=lambda **kw:self.serials[role]))
        self.registry=DeviceRegistry(factory)
        self.session=RobotSession(self.registry,Path(self.directory.name)/'config.json')
        self.addCleanup(self.cleanup)
        self.candidates={r:Candidate(r,1,2,r) for r in self.serials}
        self.session.connect(self.candidates)
        for role,access in self.session.accesses.items():
            c=calibration();access.controller.calibration=c
            access.controller.binding=RobotBinding(role,access.device_id,c.identity,tuple(
                JointBinding(n,i,'percent' if n=='gripper' else 'degrees',c.limits(n),joint_limits(role)[n])
                for i,n in enumerate(JOINT_NAMES,1)))
        self.wait(lambda:all(a.snapshot()['sample'] and a.snapshot()['sample']['observations'] for a in self.session.accesses.values()))

    def cleanup(self):
        self.session.close();self.registry.shutdown();self.assertTrue(self.registry.wait_closed(4))

    def wait(self,predicate,timeout=4):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.session.tick()
            if predicate():return
            time.sleep(.02)
        self.fail('Session transition timed out: '+self.session.error+' '+str(self.session.snapshots()))

    def record(self):
        self.session.start_recording(('leader','follower'))
        self.wait(lambda:len(self.session.record['frames'])>=3)
        self.session.stop_recording()
        return self.session.record

    def test_record_both_roundtrip_without_motor_writes(self):
        record=self.record();path=Path(self.directory.name)/'sequence.json'
        self.session.save_recording(path);self.assertEqual(load_recording(path),json.loads(json.dumps(record)))
        self.assertFalse(self.session.unsaved)
        for serial in self.serials.values():self.assertEqual(serial.writes,[])
        for bad in (-.5,float('nan'),True):
            value=copy.deepcopy(record);value['frames'][0]['t']=bad
            with self.assertRaises(ValueError):validate_recording(value)

    def test_follow_writes_only_follower_and_focus_loss_releases(self):
        self.session.start_motion('follow');self.wait(lambda:self.session.mode=='follow')
        self.wait(lambda:any(a==42 for _,a,_,_ in self.serials['follower'].writes))
        self.assertEqual(self.serials['leader'].writes,[])
        self.session.tick(active_window=False)
        self.assertEqual(self.session.mode,'idle')
        self.wait(lambda:all(r[40]==0 for r in self.serials['follower'].registers.values()))

    def test_stale_leader_stops_follow_and_recording(self):
        self.session.start_recording(('leader',));self.session.start_motion('follow')
        self.wait(lambda:self.session.mode=='follow');self.serials['leader'].drop=True
        self.wait(lambda:self.session.mode=='idle' and not self.session.recording)
        self.wait(lambda:all(r[40]==0 for r in self.serials['follower'].registers.values()))

    def test_playback_identity_rejected_before_arm_and_valid_playback_completes(self):
        record=copy.deepcopy(self.record());bad=copy.deepcopy(record)
        bad['devices']['follower']['device_id']='wrong'
        with self.assertRaises(ValueError):self.session.start_motion('playback',recording=bad)
        self.assertEqual(self.serials['follower'].writes,[])
        self.session.start_motion('playback',recording=record)
        self.wait(lambda:self.session.mode=='idle',timeout=6)
        self.assertIn('Playback complete',self.session.error)

    def test_setup_cannot_seize_session(self):
        with self.assertRaises(ValueError):self.registry.acquire(self.candidates['leader'],'leader','setup')
        observer=self.registry.acquire(self.candidates['leader'],'leader','hardware')
        self.assertFalse(observer.writable)
        with self.assertRaises(ValueError):observer.request('arm')
        self.session.close()
        deadline=time.monotonic()+3
        while not observer.writable and time.monotonic()<deadline:observer.heartbeat();time.sleep(.01)
        self.assertTrue(observer.writable)
