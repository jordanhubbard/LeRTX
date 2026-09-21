"""Portable fixed-step simulation clock (no native SDK dependency).

Decouples physics stepping from the UI/render frame rate: ``advance`` is
driven by wall-clock deltas and returns how many fixed physics substeps
should run, bounded so a slow frame cannot cause unbounded catch-up.
"""
from __future__ import annotations


class SimulationClock:
    def __init__(self, timestep_hz: int, max_steps_per_tick: int = 8) -> None:
        if timestep_hz <= 0:
            raise ValueError("timestep_hz must be positive")
        self.timestep_hz = timestep_hz
        self.dt = 1.0 / timestep_hz
        self.max_steps_per_tick = max_steps_per_tick
        self._accumulator = 0.0
        self.sim_time = 0.0
        self.playing = False

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def reset(self) -> None:
        self._accumulator = 0.0
        self.sim_time = 0.0

    def set_timestep_hz(self, timestep_hz: int) -> None:
        if timestep_hz <= 0:
            raise ValueError("timestep_hz must be positive")
        self.timestep_hz = timestep_hz
        self.dt = 1.0 / timestep_hz
        self._accumulator = 0.0

    def advance(self, wall_dt: float) -> int:
        """Return the number of fixed physics substeps to run for this tick.

        No-op (and returns 0) while paused; camera rendering may still
        proceed independently of this call.
        """
        if not self.playing or wall_dt <= 0:
            return 0
        self._accumulator += wall_dt
        steps = 0
        while self._accumulator >= self.dt and steps < self.max_steps_per_tick:
            self._accumulator -= self.dt
            self.sim_time += self.dt
            steps += 1
        return steps
