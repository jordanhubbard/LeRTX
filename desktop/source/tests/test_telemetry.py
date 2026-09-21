from dataclasses import replace
import unittest

from lertx.telemetry import LatestSample, MockReader


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.reader = MockReader("leader", clock=lambda: self.now)
        self.stream = LatestSample(self.reader.source, "leader", clock=lambda: self.now)

    def connect(self):
        self.reader.connect()
        self.stream.connect()

    def test_disconnected_awaiting_live_frozen_stale_reconnect(self):
        self.assertIsNone(self.reader.read())
        self.assertEqual(self.stream.state, "disconnected")
        self.connect()
        self.assertEqual(self.stream.state, "awaiting sample")
        self.stream.accept(self.reader.read())
        self.assertEqual(self.stream.state, "live")
        self.reader.frozen = True
        self.now += 1.1
        self.assertIsNone(self.reader.read())
        self.assertEqual(self.stream.state, "stale")
        self.reader.disconnect()
        self.stream.disconnect()
        self.assertEqual(self.stream.state, "disconnected")
        self.connect()
        self.assertIsNone(self.stream.latest)
        self.assertEqual(self.stream.state, "awaiting sample")
        self.reader.frozen = False
        self.stream.accept(self.reader.read())
        self.assertEqual(self.stream.state, "live")

    def test_complete_degree_pose_and_gripper_percent_remain_distinct(self):
        self.connect()
        self.reader.set_pose([1, 2, 3, 4, 5], 75)
        sample = self.reader.read()
        self.stream.accept(sample)
        self.assertEqual(sample.degrees, (1, 2, 3, 4, 5))
        self.assertEqual(sample.gripper_percent, 75)
        follower = MockReader("follower")
        follower.connect()
        self.assertEqual(follower.read().degrees, (0,)*5)

    def test_invalid_or_wrong_identity_never_replaces_last_sample(self):
        self.connect()
        sample = self.reader.read()
        self.stream.accept(sample)
        for changes in ({"role":"follower"}, {"source":"physical:port"},
                        {"sequence":True}, {"sequence":0}, {"timestamp":11},
                        {"timestamp":float("nan")}, {"degrees":(1,2)},
                        {"degrees":(True,0,0,0,0)}, {"degrees":(float("inf"),)*5},
                        {"gripper_percent":101}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.stream.accept(replace(sample, **changes))
            self.assertIs(self.stream.latest, sample)
        self.stream.disconnect()
        with self.assertRaises(ValueError):
            self.stream.accept(replace(sample, sequence=100))

    def test_nonmonotonic_sequence_or_timestamp_is_rejected(self):
        self.connect()
        sample = self.reader.read()
        self.stream.accept(sample)
        for invalid in (sample, replace(sample, sequence=2, timestamp=9)):
            with self.assertRaises(ValueError):
                self.stream.accept(invalid)

    def test_mock_invalid_input_is_atomic(self):
        self.reader.set_pose((1,2,3,4,5), 25)
        for degrees, grip in (((1,2),25), ((0,)*5,-1), ((181,)*5,0)):
            with self.assertRaises(ValueError):
                self.reader.set_pose(degrees, grip)
            self.assertEqual(self.reader.degrees, (1,2,3,4,5))
            self.assertEqual(self.reader.gripper_percent, 25)
