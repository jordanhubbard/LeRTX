"""Calibrated observation-to-USD mapping. This module performs no device I/O.

Input values are already normalized by LeRobot, not raw encoder ticks. A binding
contains two measured correspondences per joint; model limits cannot establish a
physical encoder zero or direction. Serial reading and actuation are separate.
"""
from dataclasses import dataclass
import math

from .robot import JOINT_NAMES, ROOTS, joint_limits


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class JointBinding:
    name: str
    motor_id: int
    unit: str
    observed: tuple[float, float]
    radians: tuple[float, float]

    def validate(self, role):
        if self.name not in JOINT_NAMES or type(self.motor_id) is not int or self.motor_id != JOINT_NAMES.index(self.name) + 1:
            raise ValueError('Joint name and expected SO-101 motor ID do not match')
        allowed = ('percent',) if self.name == 'gripper' else ('degrees', 'normalized')
        if self.unit not in allowed:
            raise ValueError('Wrong observation unit for SO-101 joint')
        if len(self.observed) != 2 or len(self.radians) != 2 or not all(map(finite, (*self.observed, *self.radians))):
            raise ValueError('Two finite calibration correspondences are required')
        if self.observed[0] == self.observed[1] or self.radians[0] == self.radians[1]:
            raise ValueError('Calibration correspondences must be distinct')
        low, high = joint_limits(role)[self.name]
        if not all(low <= angle <= high for angle in self.radians):
            raise ValueError('Calibration exceeds virtual joint limits')
        if self.unit != 'degrees':
            minimum = 0 if self.unit == 'percent' else -100
            if not all(minimum <= value <= 100 for value in self.observed):
                raise ValueError('Calibration exceeds observation range')

    def convert(self, value):
        if not finite(value) or not min(self.observed) <= value <= max(self.observed):
            raise ValueError('Observation is outside calibrated range')
        fraction = (value - self.observed[0]) / (self.observed[1] - self.observed[0])
        return self.radians[0] + fraction * (self.radians[1] - self.radians[0])


@dataclass(frozen=True)
class RobotBinding:
    role: str
    device_id: str
    calibration_id: str
    joints: tuple[JointBinding, ...]

    def __post_init__(self):
        if self.role not in ROOTS or not self.device_id.strip() or not self.calibration_id.strip():
            raise ValueError('Role, device and calibration identity are required')
        if len(self.joints) != 6 or {j.name for j in self.joints} != set(JOINT_NAMES):
            raise ValueError('Exactly one binding per SO-101 joint is required')
        for joint in self.joints:
            joint.validate(self.role)

    def map_observation(self, values, *, device_id, calibration_id, captured_at, now, max_age=.25):
        if device_id != self.device_id or calibration_id != self.calibration_id:
            raise ValueError('Observation device or calibration identity mismatch')
        if not all(map(finite, (captured_at, now, max_age))) or max_age <= 0 or not 0 <= now - captured_at <= max_age:
            raise ValueError('Observation timestamp is stale or invalid')
        if any(j.name + '.pos' not in values for j in self.joints):
            raise ValueError('Observation is missing required joint positions')
        return {ROOTS[self.role] + '/Physics/' + j.name: j.convert(values[j.name + '.pos'])
                for j in self.joints}
