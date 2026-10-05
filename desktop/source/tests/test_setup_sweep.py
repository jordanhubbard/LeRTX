"""Automatic travel capture must use selected-joint evidence, not bus-wide motion."""
import unittest
from lertx.setup_calibration import JointSweep
from lertx.robot import JOINT_NAMES


class JointSweepTests(unittest.TestCase):
    def setUp(self):
        self.sweep=JointSweep('follower','shoulder_pan')
        self.sequence=0;self.timestamp=0.

    def feed(self,value,*,gap=.05,duplicate=False):
        self.timestamp+=gap
        if not duplicate:self.sequence+=1
        motors={i:{'position':(1100+self.sequence*37+i*50)%4096,'torque':False} for i in range(1,7)}
        motors[1]['position']=value
        self.sweep.observe(dict(sequence=self.sequence,timestamp=self.timestamp,motors=motors))

    def hold(self,value,count=18):
        for _ in range(count):self.feed(value)

    def test_full_sweep_completes_despite_other_joints_moving(self):
        self.feed(2047);self.hold(1600)
        self.assertEqual(self.sweep.phase,1)
        self.hold(2500);self.assertEqual(self.sweep.phase,2)
        self.hold(1600);self.assertTrue(self.sweep.complete)
        self.assertEqual(self.sweep.bounds,[1600,2500])
        self.assertEqual(self.sweep.progress,100)
        self.assertIsNotNone(self.sweep.ready_sequence)

    def test_jitter_and_other_joint_motion_never_capture_an_endpoint(self):
        for i in range(100):self.feed(2047+(-1 if i%2 else 1)*5)
        self.assertEqual(self.sweep.phase,0)
        self.assertFalse(self.sweep.complete)

    def test_small_sweep_and_one_way_motion_are_insufficient(self):
        self.feed(2047);self.hold(1600);self.hold(1700)
        self.assertEqual(self.sweep.phase,1)
        self.hold(2500);self.hold(2500)
        self.assertEqual(self.sweep.phase,2)
        self.assertFalse(self.sweep.complete)

    def test_duplicate_samples_cannot_supply_dwell(self):
        self.feed(2047);self.feed(1600)
        for _ in range(30):self.feed(1600,duplicate=True)
        self.assertEqual(self.sweep.phase,0)

    def test_stale_gaps_do_not_count_as_a_hold(self):
        self.feed(2047)
        for _ in range(20):self.feed(1600,gap=.3)
        self.assertEqual(self.sweep.phase,0)
        self.hold(1600);self.assertEqual(self.sweep.phase,1)

    def test_single_encoder_spike_does_not_set_an_endpoint(self):
        self.feed(2047);self.feed(4000);self.hold(2047)
        self.assertEqual(self.sweep.phase,0)
        self.hold(1600);self.hold(2500);self.hold(1600)
        self.assertEqual(self.sweep.bounds,[1600,2500])

    def test_all_joints_have_meaningful_travel_thresholds(self):
        for role in ('leader','follower'):
            for name in JOINT_NAMES:
                sweep=JointSweep(role,name)
                self.assertGreaterEqual(sweep.minimum_span,160)
                self.assertLessEqual(sweep.minimum_span,600)
