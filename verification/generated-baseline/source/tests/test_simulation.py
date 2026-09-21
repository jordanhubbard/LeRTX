import unittest

from lertx.simulation import SimulationClock


class SimulationClockTests(unittest.TestCase):
    def test_paused_clock_does_not_advance(self):
        clock = SimulationClock(timestep_hz=60)
        self.assertEqual(clock.advance(1.0), 0)
        self.assertEqual(clock.sim_time, 0.0)

    def test_play_advances_fixed_steps_independent_of_frame_rate(self):
        clock = SimulationClock(timestep_hz=100)
        clock.play()
        steps_fast = clock.advance(0.01)
        self.assertEqual(steps_fast, 1)

        clock2 = SimulationClock(timestep_hz=100)
        clock2.play()
        steps_slow_accumulated = 0
        for _ in range(10):
            steps_slow_accumulated += clock2.advance(0.001)
        self.assertEqual(steps_slow_accumulated, 1)
        self.assertLess(abs(clock.sim_time - clock2.sim_time), 1e-9)

    def test_reset_zeroes_time_and_accumulator(self):
        clock = SimulationClock(timestep_hz=60)
        clock.play()
        clock.advance(1.0)
        self.assertGreater(clock.sim_time, 0.0)
        clock.reset()
        self.assertEqual(clock.sim_time, 0.0)
        clock.play()
        self.assertEqual(clock.advance(1.0 / 60.0), 1)

    def test_pause_leaves_sim_time_unchanged_between_calls(self):
        clock = SimulationClock(timestep_hz=60)
        clock.play()
        clock.advance(1.0 / 60.0)
        time_after_step = clock.sim_time
        clock.pause()
        clock.advance(5.0)
        self.assertEqual(clock.sim_time, time_after_step)

    def test_bounded_catch_up_caps_steps_per_tick(self):
        clock = SimulationClock(timestep_hz=1000, max_steps_per_tick=4)
        clock.play()
        self.assertEqual(clock.advance(1.0), 4)


if __name__ == "__main__":
    unittest.main()
