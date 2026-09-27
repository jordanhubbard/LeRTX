import dataclasses
import unittest
from lertx.joint_binding import JointBinding, RobotBinding
from lertx.robot import JOINT_NAMES


class JointBindingTests(unittest.TestCase):
    def binding(self):
        return RobotBinding('leader', 'test-arm', 'measured-session-1', tuple(
            JointBinding(name, index+1, 'percent' if name=='gripper' else 'degrees',
                         (0.,100.) if name=='gripper' else (-20.,20.),
                         (.1,.7) if name=='gripper' else (.3,-.3))
            for index,name in enumerate(JOINT_NAMES)))

    def test_name_mapping_direction_offset_and_timestamp(self):
        binding=self.binding()
        values={name+'.pos':50. if name=='gripper' else -10. for name in reversed(JOINT_NAMES)}
        mapped=binding.map_observation(values,device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1)
        self.assertAlmostEqual(mapped['/World/Leader/Physics/gripper'],.4)
        self.assertAlmostEqual(mapped['/World/Leader/Physics/shoulder_pan'],.15)
        for overrides in ({'device_id':'wrong'},{'calibration_id':'wrong'},{'now':11.},{'captured_at':11.}):
            arguments=dict(device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1);arguments.update(overrides)
            with self.assertRaises(ValueError):binding.map_observation(values,**arguments)
        for invalid in (float('nan'),True,300.):
            values['elbow_flex.pos']=invalid
            with self.assertRaises(ValueError):binding.map_observation(values,device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1)

    def test_invalid_bindings_fail_before_observation(self):
        binding=self.binding()
        for joints in (binding.joints[:-1], binding.joints[:-1]+(binding.joints[0],),
                       (dataclasses.replace(binding.joints[0],motor_id=6),)+binding.joints[1:],
                       binding.joints[:-1]+(dataclasses.replace(binding.joints[-1],unit='degrees'),)):
            with self.assertRaises(ValueError):dataclasses.replace(binding,joints=joints)
