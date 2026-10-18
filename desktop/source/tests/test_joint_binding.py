import dataclasses
import unittest
from lertx.joint_binding import JointBinding, RobotBinding
from lertx.robot import JOINT_NAMES


class JointBindingTests(unittest.TestCase):
    def test_preview_reports_excess_without_weakening_command_mapping(self):
        binding=self.binding();values={n+'.pos':50. if n=='gripper' else 0. for n in JOINT_NAMES}
        values['elbow_flex.pos']=-30.
        arguments=dict(device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1)
        mapped,warnings=binding.map_preview(values,**arguments)
        self.assertEqual(len(mapped),6);self.assertTrue(any('elbow_flex' in w for w in warnings))
        with self.assertRaises(ValueError):binding.map_observation(values,**arguments)
        with self.assertRaises(ValueError):binding.map_preview(values,**{**arguments,'now':12.})

    def test_wizard_gripper_uses_normalized_travel_and_custom_binding_is_retained(self):
        from lertx.robot import joint_limits
        binding=self.binding();values={n+'.pos':50. if n=='gripper' else 0. for n in JOINT_NAMES}
        arguments=dict(device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1)
        custom,_=binding.map_preview(values,**arguments)
        wizard,_=binding.map_preview(values,**arguments,normalize_gripper=True)
        self.assertAlmostEqual(custom['/World/Leader/Physics/gripper'],.4)
        self.assertAlmostEqual(wizard['/World/Leader/Physics/gripper'],sum(joint_limits('leader')['gripper'])/2)

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

    def test_reports_every_out_of_range_joint_without_partial_mapping(self):
        binding=self.binding()
        values={name+'.pos':50. if name=='gripper' else 0. for name in JOINT_NAMES}
        values.update({'elbow_flex.pos':-30.,'gripper.pos':101.})
        with self.assertRaises(ValueError) as error:
            binding.map_observation(values,device_id='test-arm',calibration_id='measured-session-1',captured_at=10.,now=10.1)
        self.assertIn('elbow_flex',str(error.exception))
        self.assertIn('gripper',str(error.exception))
