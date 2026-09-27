"""Independent checks of the standard USD assets and their URDF contract."""
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pxr import Gf, Usd, UsdGeom, UsdPhysics

from lertx.robot import RESOURCES, ROLES, JOINT_NAMES, author_pair, follower_targets, home_positions


def rotation(rpy):
    # URDF fixed-axis roll, pitch, yaw, applied to column vectors.
    import numpy as np
    r, p, y = map(float, rpy.split())
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
    return np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],
                     [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])


class RobotAssetTests(unittest.TestCase):
    def test_standard_joint_frames_limits_and_mass_match_urdf(self):
        import numpy as np
        for role in ROLES:
            source = RESOURCES / ('so101_leader_new_calib.urdf' if role=='leader' else 'so101_new_calib.urdf')
            urdf = ET.parse(source).getroot()
            stage = Usd.Stage.Open(str(RESOURCES / (role+'.usdc')))
            self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage), 1.)
            self.assertEqual(UsdGeom.GetStageUpAxis(stage), 'Z')
            usd_joints = {p.GetName(): UsdPhysics.RevoluteJoint(p) for p in stage.Traverse() if p.IsA(UsdPhysics.RevoluteJoint)}
            self.assertEqual(set(usd_joints), set(JOINT_NAMES))
            for j in urdf.findall('joint'):
                if j.get('type')!='revolute': continue
                joint=usd_joints[j.get('name')]
                parent=stage.GetPrimAtPath(joint.GetBody0Rel().GetTargets()[0]);child=stage.GetPrimAtPath(joint.GetBody1Rel().GetTargets()[0])
                self.assertEqual(parent.GetName(), j.find('parent').get('link'))
                self.assertEqual(child.GetName(), j.find('child').get('link'))
                np.testing.assert_allclose(joint.GetLocalPos0Attr().Get(), list(map(float,j.find('origin').get('xyz').split())),atol=1e-6)
                np.testing.assert_allclose(joint.GetLocalPos1Attr().Get(), [0,0,0],atol=1e-6)
                unit = Gf.Vec3d(*({'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[joint.GetAxisAttr().Get()]))
                actual = Gf.Rotation(Gf.Quatd(joint.GetLocalRot0Attr().Get())).TransformDir(unit)
                expected = rotation(j.find('origin').get('rpy')) @ np.array(list(map(float,j.find('axis').get('xyz').split())))
                np.testing.assert_allclose(actual, expected,atol=1e-6)
                for attr,key in [(joint.GetLowerLimitAttr(),'lower'),(joint.GetUpperLimitAttr(),'upper')]:
                    self.assertAlmostEqual(math.radians(attr.Get()),float(j.find('limit').get(key)),places=6)
            for link in urdf.findall('link'):
                if not link.findall('visual'):continue
                prim=next(p for p in stage.Traverse() if p.GetName()==link.get('name'))
                mass=UsdPhysics.MassAPI(prim);inertial=link.find('inertial')
                self.assertAlmostEqual(mass.GetMassAttr().Get(),float(inertial.find('mass').get('value')),places=6)
                np.testing.assert_allclose(mass.GetCenterOfMassAttr().Get(),list(map(float,inertial.find('origin').get('xyz').split())),atol=1e-6)
                vals={k:float(v) for k,v in inertial.find('inertia').attrib.items()}
                tensor=np.array([[vals['ixx'],vals['ixy'],vals['ixz']],[vals['ixy'],vals['iyy'],vals['iyz']],[vals['ixz'],vals['iyz'],vals['izz']]])
                rot=rotation(inertial.find('origin').get('rpy'))
                axes=np.array(Gf.Matrix3d(Gf.Quatd(mass.GetPrincipalAxesAttr().Get()))).T
                np.testing.assert_allclose(axes @ np.diag(mass.GetDiagonalInertiaAttr().Get()) @ axes.T,rot @ tensor @ rot.T,atol=1e-9)

    def test_saved_pair_has_no_external_dependencies_and_valid_relationships(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pair.usdc'
            stage=Usd.Stage.CreateNew(str(path));UsdGeom.Xform.Define(stage,'/World')
            author_pair(stage);stage.GetRootLayer().Save()
            reopened=Usd.Stage.Open(str(path))
            self.assertEqual(len([p for p in reopened.Traverse() if p.IsA(UsdPhysics.RevoluteJoint)]),12)
            for prim in reopened.Traverse():
                self.assertFalse(prim.HasAuthoredReferences())
                for rel in prim.GetRelationships():
                    for target in rel.GetTargets():self.assertTrue(reopened.GetObjectAtPath(target),str(target))
            self.assertEqual(len([layer for layer in reopened.GetUsedLayers() if not layer.anonymous]),1)

    def test_trigger_maps_full_travel_and_home_consistently(self):
        from lertx.robot import joint_limits
        leader=home_positions('leader')
        self.assertAlmostEqual(follower_targets(leader)['gripper'],home_positions('follower')['gripper'])
        for index in [0,1]:
            leader['gripper']=joint_limits('leader')['gripper'][index]
            self.assertAlmostEqual(follower_targets(leader)['gripper'],joint_limits('follower')['gripper'][index])
