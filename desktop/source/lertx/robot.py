"""Pinned SO-101 descriptions, self-contained USD geometry and Newton articulations.

The upstream leader trigger is a CAD estimate, not a calibrated physical device.
See resources/so101/README.md and provenance.json for the exact source and license.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

RESOURCES = Path(__file__).with_name('resources') / 'so101'
JOINT_NAMES = ('shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper')
ROLES = ('leader', 'follower')
ROOTS = {role: '/World/' + role.title() for role in ROLES}


def numbers(text, default='0 0 0'):
    return tuple(float(x) for x in (text or default).split())


def origin(element):
    import warp as wp
    node = element.find('origin')
    return wp.transform(numbers(node.get('xyz')), wp.quat_rpy(*numbers(node.get('rpy')))) if node is not None else wp.transform_identity()


@functools.lru_cache(maxsize=2)
def description(role):
    if role not in ROLES:
        raise ValueError('Unknown robot role')
    name = 'so101_leader_new_calib.urdf' if role == 'leader' else 'so101_new_calib.urdf'
    data = (RESOURCES/name).read_bytes()
    provenance = json.loads((RESOURCES/'provenance.json').read_text())
    if hashlib.sha256(data).hexdigest() != provenance['files']['Simulation/SO101/'+name]:
        raise ValueError('SO-101 model identity mismatch')
    root = ET.fromstring(data)
    links = {x.get('name'): x for x in root.findall('link')}
    joints = {x.get('name'): x for x in root.findall('joint')}
    if {n for n,j in joints.items() if j.get('type')!='fixed'} != set(JOINT_NAMES):
        raise ValueError('Unexpected SO-101 joint topology')
    return data.decode(), links, joints


def joint_limits(role):
    joints = description(role)[2]
    return {name: (float(joints[name].find('limit').get('lower')),
                   float(joints[name].find('limit').get('upper'))) for name in JOINT_NAMES}


def home_positions(role):
    # Zero is the upstream mid-range arm convention. Both grippers start open.
    return {name: (sum((joint_limits(role)[name][0] * .4, joint_limits(role)[name][1] * .6)) if name == 'gripper' else 0.) for name in JOINT_NAMES}


def follower_targets(leader):
    result = dict(leader)
    low, high = joint_limits('leader')['gripper']
    fraction = max(0., min(1., (leader['gripper'] - low)/(high-low)))
    low, high = joint_limits('follower')['gripper']
    result['gripper'] = low + fraction*(high-low)
    return {name: max(joint_limits('follower')[name][0], min(joint_limits('follower')[name][1], result[name])) for name in JOINT_NAMES}


def forward_kinematics(role, positions, base=None):
    import warp as wp
    links, joints = description(role)[1:]
    poses = {'base_link': base or wp.transform_identity()}
    for name in JOINT_NAMES:
        joint = joints[name]
        parent, child = joint.find('parent').get('link'), joint.find('child').get('link')
        poses[child] = poses[parent] * origin(joint) * wp.transform((0., 0., 0.), wp.quat_from_axis_angle(wp.vec3(*numbers(joint.find('axis').get('xyz'))), positions[name]))
    for joint in joints.values():
        if joint.get('type')=='fixed':
            poses[joint.find('child').get('link')] = poses[joint.find('parent').get('link')] * origin(joint)
    if set(poses) != set(links):
        raise ValueError('Disconnected SO-101 link')
    return poses


@functools.lru_cache(maxsize=24)
def stl_mesh(name):
    import numpy as np
    path = (RESOURCES/name).resolve()
    if not path.is_relative_to(RESOURCES.resolve()):
        raise ValueError('Robot mesh path escapes model directory')
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + count*50:
        raise ValueError('Invalid binary robot STL')
    dtype = np.dtype([('normal','<f4',(3,)), ('points','<f4',(3,3)), ('attribute','<u2')])
    points = np.frombuffer(data, dtype=dtype, offset=84)['points'].reshape(-1,3)
    vertices, indices = np.unique(points, axis=0, return_inverse=True)
    return vertices.astype('float32'), indices.astype('int32')


@functools.lru_cache(maxsize=24)
def collision_mesh(name):
    import numpy as np
    data=json.loads((RESOURCES/'collision-hulls.json').read_text())['parts'][name]
    if hashlib.sha256((RESOURCES/name).read_bytes()).hexdigest()!=data['source_sha256']:
        raise ValueError('Collision hull source identity mismatch')
    return np.asarray(data['vertices'],dtype='float32'), np.asarray(data['triangles'],dtype='int32').reshape(-1)


def gf_matrix(pose):
    from pxr import Gf
    q = pose.q
    t = Gf.Transform()
    t.SetTranslation(Gf.Vec3d(*map(float, pose.p)))
    t.SetRotation(Gf.Rotation(Gf.Quatd(float(q[3]), Gf.Vec3d(*map(float, q[:3])))))
    return t.GetMatrix()


def author_pair(stage):
    """Embed officially converted USD, including standard joints and physics data."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade
    for role, x in (('leader', -.32), ('follower', .32)):
        root_path = ROOTS[role]
        stage.DefinePrim('/World', 'Xform')
        source = RESOURCES / (role + '.usdc')
        manifest = json.loads((RESOURCES / 'usd-provenance.json').read_text())
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['files'][source.name]:
            raise ValueError('Converted robot USD identity mismatch')
        # Reference first so composition remaps all internal relationships. Flatten
        # into the document so saved workspaces are independent of installed assets.
        temporary = Usd.Stage.CreateInMemory()
        root = temporary.DefinePrim(root_path, 'Xform')
        root.GetReferences().AddReference(str(source))
        for prim in temporary.Traverse():
            if prim.IsInstance():
                prim.SetInstanceable(False)
        if not Sdf.CopySpec(temporary.Flatten(), root_path, stage.GetRootLayer(), root_path):
            raise ValueError('Could not embed robot USD')
        root = stage.GetPrimAtPath(root_path)
        for key, value in {'robotRole': role, 'robotDescription': description(role)[0],
                           'collisionApproximation': 'convex hull per URDF mechanical part',
                           'robotModel': 'so101.v1'}.items():
            root.CreateAttribute('lertx:' + key, Sdf.ValueTypeNames.String).Set(value)
        UsdGeom.Xformable(root).MakeMatrixXform().Set(Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(x, 0, .01)))
        positions = home_positions(role)
        root.CreateAttribute('lertx:jointPositions', Sdf.ValueTypeNames.String).Set(json.dumps(positions, sort_keys=True))
        for motor_id, name in enumerate(JOINT_NAMES, 1):
            joint = stage.GetPrimAtPath(root_path + '/Physics/' + name)
            joint.CreateAttribute('lertx:jointName', Sdf.ValueTypeNames.String).Set(name)
            joint.CreateAttribute('lertx:expectedMotorId', Sdf.ValueTypeNames.Int).Set(motor_id)
            joint.CreateAttribute('lertx:bindingState', Sdf.ValueTypeNames.String).Set('unbound')
        mount = UsdPhysics.FixedJoint(stage.GetPrimAtPath(root_path + '/Physics/root_joint'))
        mount.CreateLocalPos0Attr(Gf.Vec3f(x, 0, .01))
        poses = forward_kinematics(role, positions)
        # Converter links are hierarchical. Preserve that structure and author
        # relative home poses; the renderer receives world transforms at runtime.
        for prim in Usd.PrimRange(root):
            name = prim.GetName()
            if prim.HasAPI(UsdPhysics.RigidBodyAPI) and name in poses:
                parent_name = prim.GetParent().GetName()
                local = gf_matrix(poses[name])
                if parent_name in poses:
                    local = local * gf_matrix(poses[parent_name]).GetInverse()
                UsdGeom.Xformable(prim).MakeMatrixXform().Set(local)
                if name == 'base_link':
                    UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(True)
            if prim.IsA(UsdShade.Shader):
                color = UsdShade.Shader(prim).GetInput('diffuseColor')
                if color and '3d_printed' in str(prim.GetPath()):
                    color.DisconnectSource()
                    color.Set(Gf.Vec3f(*((.12,.68,.62) if role=='leader' else (.95,.64,.12))))


def robot_ancestor(prim):
    while prim and not prim.IsPseudoRoot():
        if prim.GetAttribute('lertx:robotModel').Get():
            return prim
        prim = prim.GetParent()
    return None


def add_articulations(stage, builder, mapping, scales):
    import numpy as np
    import newton
    import warp as wp
    from pxr import Usd, UsdGeom, UsdPhysics
    result = {}
    for root in stage.Traverse():
        if root.GetAttribute('lertx:robotModel').Get() is None:
            continue
        role = root.GetAttribute('lertx:robotRole').Get()
        if role not in ROLES or role in result or root.GetAttribute('lertx:robotModel').Get()!='so101.v1' or root.GetAttribute('lertx:robotDescription').Get()!=description(role)[0]:
            raise ValueError('Unrecognized or modified SO-101 articulation')
        if UsdGeom.GetStageMetersPerUnit(stage)!=1. or str(UsdGeom.GetStageUpAxis(stage))!='Z':
            raise ValueError('SO-101 articulation requires metric Z-up stage')
        matrix = UsdGeom.Xformable(root).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        from pxr import Gf
        transform = Gf.Transform(matrix)
        if any(abs(float(v)-1)>1e-5 for v in transform.GetScale()):
            raise ValueError('Robot articulation cannot be scaled')
        q=matrix.ExtractRotationQuat()
        base=wp.transform(tuple(matrix.ExtractTranslation()),(*q.GetImaginary(),q.GetReal()))
        positions=json.loads(root.GetAttribute('lertx:jointPositions').Get())
        if set(positions)!=set(JOINT_NAMES) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not joint_limits(role)[n][0]<=v<=joint_limits(role)[n][1] for n,v in positions.items()):
            raise ValueError('Invalid authored SO-101 joint positions')
        poses=forward_kinematics(role,positions,base)
        bodies={}
        link_paths = {p.GetName(): str(p.GetPath()) for p in Usd.PrimRange(root)
                      if p.HasAPI(UsdPhysics.RigidBodyAPI)}
        for name,link in description(role)[1].items():
            if not link.findall('visual'):
                continue
            path=link_paths[name]
            inertial=link.find('inertial'); tensor=inertial.find('inertia')
            vals={k:float(v) for k,v in tensor.attrib.items()}
            inertia=np.array([[vals['ixx'],vals['ixy'],vals['ixz']],[vals['ixy'],vals['iyy'],vals['iyz']],[vals['ixz'],vals['iyz'],vals['izz']]])
            rot=np.array(wp.quat_to_matrix(origin(inertial).q)).reshape(3,3)
            body=builder.add_link(xform=poses[name],mass=float(inertial.find('mass').get('value')),com=origin(inertial).p,inertia=wp.mat33(rot@inertia@rot.T),lock_inertia=True,is_kinematic=(name=="base_link"),label=path)
            bodies[name]=body;mapping.add(body,path);scales[body]=(1.,1.,1.)
            for i,collision in enumerate(link.findall('collision')):
                mesh=collision.find('geometry/mesh')
                vertices,indices=collision_mesh(mesh.get('filename'))
                builder.add_shape_convex_hull(body,xform=origin(collision),mesh=newton.Mesh(vertices,indices,compute_inertia=False),cfg=newton.ModelBuilder.ShapeConfig(density=0.,mu=.7,margin=.0005),label=path+f'/collision_{i}')
        joints=[builder.add_joint_fixed(-1,bodies['base_link'],parent_xform=base,label=str(root.GetPath())+'/mount')]
        indices={}
        for name in JOINT_NAMES:
            joint=description(role)[2][name];low,high=joint_limits(role)[name]
            index=builder.add_joint_revolute(bodies[joint.find('parent').get('link')],bodies[joint.find('child').get('link')],parent_xform=origin(joint),axis=numbers(joint.find('axis').get('xyz')),limit_lower=low,limit_upper=high,target_pos=positions[name],target_ke=1000.,target_kd=0.,label=str(root.GetPath())+'/'+name)
            builder.joint_q[builder.joint_q_start[index]]=positions[name]
            indices[name]=index;joints.append(index)
        builder.add_articulation(joints,label=str(root.GetPath()))
        result[role]={'joints':indices,'bodies':bodies,'positions':positions}
    return result
