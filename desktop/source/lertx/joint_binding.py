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
            raise ValueError(f'{self.name}: observation {value!r} is outside calibrated binding range '
                             f'[{min(self.observed):.3f}, {max(self.observed):.3f}] {self.unit}')
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

    def _check_sample(self,values,device_id,calibration_id,captured_at,now,max_age):
        if device_id != self.device_id or calibration_id != self.calibration_id:
            raise ValueError('Observation device or calibration identity mismatch')
        if not all(map(finite, (captured_at, now, max_age))) or max_age <= 0 or not 0 <= now - captured_at <= max_age:
            raise ValueError('Observation timestamp is stale or invalid')
        if any(j.name + '.pos' not in values for j in self.joints):
            raise ValueError('Observation is missing required joint positions')

    def map_preview(self,values,*,device_id,calibration_id,captured_at,now,normalize_gripper=False,max_age=.25):
        """Read-only display; never use this result to derive motor commands."""
        self._check_sample(values,device_id,calibration_id,captured_at,now,max_age)
        mapped={};warnings=[]
        for joint in self.joints:
            value=values[joint.name+'.pos']
            if not finite(value):raise ValueError(joint.name+': invalid measured position')
            if normalize_gripper and joint.name=='gripper':
                low,high=joint_limits(self.role)[joint.name]
                fraction=max(0.,min(1.,value/100.))
                if (joint.radians[1]-joint.radians[0])*(joint.observed[1]-joint.observed[0])<0:fraction=1-fraction
                angle=low+fraction*(high-low)
                if not 0<=value<=100:warnings.append(joint.name+': outside captured travel')
            else:
                fraction=(value-joint.observed[0])/(joint.observed[1]-joint.observed[0])
                angle=joint.radians[0]+fraction*(joint.radians[1]-joint.radians[0])
                if not 0<=fraction<=1:warnings.append(joint.name+': beyond paired mapping interval')
            if abs(angle)>2*math.pi:raise ValueError(joint.name+': implausible preview rotation; review binding')
            mapped[ROOTS[self.role]+'/Physics/'+joint.name]=angle
        return mapped,warnings

    def map_observation(self, values, *, device_id, calibration_id, captured_at, now, max_age=.25):
        self._check_sample(values,device_id,calibration_id,captured_at,now,max_age)
        mapped={};errors=[]
        for joint in self.joints:
            try:mapped[ROOTS[self.role]+'/Physics/'+joint.name]=joint.convert(values[joint.name+'.pos'])
            except ValueError as exc:errors.append(str(exc))
        if errors:raise ValueError('; '.join(errors))
        return mapped
