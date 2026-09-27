"""Metric Newton simulation with explicit authored-USD body identities."""
from __future__ import annotations

import math

from .scene import BodyMapping, SimulationDisabledError


def build_model(stage, gravity=-9.81):
    import newton
    import warp as wp
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    units = UsdGeom.GetStageMetersPerUnit(stage)
    if not math.isfinite(units) or units <= 0:
        raise SimulationDisabledError("Invalid stage metersPerUnit")
    axis = str(UsdGeom.GetStageUpAxis(stage))
    gravity_vector = tuple(gravity if a == axis else 0.0 for a in "XYZ")
    builder = newton.ModelBuilder(up_axis=axis, gravity=gravity_vector)
    mapping, scales = BodyMapping(), {}
    from .robot import robot_ancestor, add_articulations
    for prim in stage.Traverse():
        if robot_ancestor(prim):
            continue
        rigid = prim.HasAPI(UsdPhysics.RigidBodyAPI)
        collision = prim.HasAPI(UsdPhysics.CollisionAPI)
        if not (rigid or collision):
            continue
        path = str(prim.GetPath())

        def reject(reason):
            raise SimulationDisabledError(f"{path}: {reason}; physics disabled")

        ancestor = prim.GetParent()
        while ancestor and not ancestor.IsPseudoRoot():
            if ancestor.HasAPI(UsdPhysics.RigidBodyAPI):
                reject("nested rigid bodies or child colliders are not supported")
            ancestor = ancestor.GetParent()
        if rigid:
            api = UsdPhysics.RigidBodyAPI(prim)
            if api.GetKinematicEnabledAttr().Get() or not api.GetRigidBodyEnabledAttr().Get():
                reject("kinematic or disabled rigid body")
            if not collision:
                reject("rigid body requires a supported collider on the same prim")
        if collision and not UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
            reject("disabled collider")
        if not (prim.IsA(UsdGeom.Cube) or prim.IsA(UsdGeom.Sphere)):
            reject("unsupported collider geometry")
        xf = UsdGeom.Xformable(prim)
        if xf.TransformMightBeTimeVarying():
            reject("animated collider transform")
        matrix = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        axes = [Gf.Vec3d(*[matrix[i][j] for j in range(3)]) for i in range(3)]
        scale = [v.GetLength() for v in axes]
        if any(not math.isfinite(s) or s <= 1e-12 for s in scale):
            reject("singular or nonfinite transform")
        if matrix.GetDeterminant() <= 0:
            reject("reflected collider transform")
        axes = [v / s for v, s in zip(axes, scale)]
        if any(abs(Gf.Dot(axes[i], axes[j])) > 1e-6 for i in range(3) for j in range(i)):
            reject("sheared collider transform")
        rotation_matrix = Gf.Matrix4d(1)
        for i in range(3):
            rotation_matrix.SetRow(i, Gf.Vec4d(*axes[i], 0))
        q = rotation_matrix.ExtractRotationQuat()
        p = matrix.ExtractTranslation() * units
        if not all(math.isfinite(x) for x in p):
            reject("nonfinite position")
        pose = wp.transform(tuple(p), (*q.GetImaginary(), q.GetReal()))
        body = -1
        if rigid:
            body = builder.add_body(xform=pose, label=path)
            mapping.add(body, path)
            scales[body] = scale
        shape_pose = wp.transform_identity() if rigid else pose
        if prim.IsA(UsdGeom.Sphere):
            if max(scale) - min(scale) > 1e-6 * max(scale):
                reject("nonuniform sphere scale")
            radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get() * scale[0] * units
            if not math.isfinite(radius) or radius <= 0:
                reject("invalid sphere radius")
            builder.add_shape_sphere(body, radius=radius, xform=shape_pose)
        else:
            size = UsdGeom.Cube(prim).GetSizeAttr().Get() * units
            if not math.isfinite(size) or size <= 0:
                reject("invalid cube size")
            builder.add_shape_box(body, hx=size*scale[0]/2, hy=size*scale[1]/2,
                                  hz=size*scale[2]/2, xform=shape_pose)
    builder._lertx_robots = add_articulations(stage, builder, mapping, scales)
    return builder, mapping, scales, units


class PhysicsScene:
    def __init__(self, stage, device="cuda:0", gravity=-9.81):
        import newton
        builder, self.mapping, self.scales, self.units = build_model(stage, gravity)
        if not self.mapping.index_to_path:
            raise SimulationDisabledError("No supported rigid bodies; physics disabled")
        self.robots = builder._lertx_robots
        self.following = True
        self.targets = {r: dict(v["positions"]) for r,v in self.robots.items()}
        self.model = builder.finalize(device=device)
        self.state, self.next_state = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.solver = newton.solvers.SolverXPBD(self.model, iterations=16 if self.robots else 2)
        import warp as wp
        self.measured_q = wp.clone(self.model.joint_q)
        self.measured_qd = wp.clone(self.model.joint_qd)
        self.q_indices = {r: {n: int(self.model.joint_q_start.numpy()[j]) for n,j in data["joints"].items()} for r,data in self.robots.items()}
        self.target_indices = {r: {n: int(self.model.joint_target_q_start.numpy()[j]) for n,j in data["joints"].items()} for r,data in self.robots.items()}
        self.pipeline = newton.CollisionPipeline(self.model)
        self.contacts = self.pipeline.contacts()
        self.time = 0.0
        self._step_graph = None
        self._step_graph_key = None
        # Attached OVStage consumes local transforms. Cache the composed parent
        # frame (which may itself move), preserving authored hierarchy and scale.
        from pxr import UsdGeom
        self.render_mapping = self.mapping
        body_paths = {path: index for index, path in self.mapping.index_to_path.items()}
        self._render_parents = []
        for index in sorted(self.mapping.index_to_path):
            prim = stage.GetPrimAtPath(self.mapping.index_to_path[index])
            parent = prim.GetParent()
            parent_world = UsdGeom.Xformable(prim).ComputeParentToWorldTransform(0)
            ancestor = parent
            while ancestor and str(ancestor.GetPath()) not in body_paths:
                ancestor = ancestor.GetParent()
            if ancestor:
                ancestor_world = UsdGeom.Xformable(ancestor).ComputeLocalToWorldTransform(0)
                self._render_parents.append((body_paths[str(ancestor.GetPath())], parent_world * ancestor_world.GetInverse()))
            else:
                self._render_parents.append((None, parent_world))

    def step(self, dt, substeps=1):
        if not math.isfinite(dt) or dt <= 0 or not 1 <= substeps <= 64:
            raise ValueError("Invalid physics step")
        if self.robots:
            substeps = max(substeps, 4)
            self._update_targets()
        import warp as wp
        if self.robots and self.model.device.is_cuda:
            substeps += substeps % 2
            key = (dt, substeps)
            if key != self._step_graph_key:
                with wp.ScopedCapture(device=self.model.device) as capture:
                    self._integrate(dt, substeps)
                self._step_graph = capture.graph
                self._step_graph_key = key
            wp.capture_launch(self._step_graph)
        else:
            self._integrate(dt, substeps)
        self.time += dt

    def _integrate(self, dt, substeps):
        for _ in range(substeps):
            self.state.clear_forces()
            self.pipeline.collide(self.state, self.contacts)
            self.solver.step(self.state, self.next_state, self.control, self.contacts, dt/substeps)
            self.state, self.next_state = self.next_state, self.state

    def robot_positions(self):
        import newton
        newton.eval_ik(self.model, self.state, self.measured_q, self.measured_qd)
        q = self.measured_q.numpy()
        return {r: {n: float(q[i]) for n,i in indices.items()} for r,indices in self.q_indices.items()}

    def command_robot(self, role, positions=None, following=None):
        from .robot import joint_limits
        if role not in self.robots:
            raise ValueError("This scene has no requested SO-101 arm")
        candidate = dict(self.targets[role])
        if positions is not None:
            limits = joint_limits(role)
            if not isinstance(positions,dict) or any(n not in limits or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not limits[n][0]<=v<=limits[n][1] for n,v in positions.items()):
                raise ValueError("Joint targets must be finite and within the model limits")
            if role == 'follower' and self.following:
                raise ValueError("Disable following before commanding the follower")
            candidate.update(positions)
        if following is not None and type(following) is not bool:
            raise ValueError("Following must be a boolean")
        self.targets[role] = candidate
        if following is not None:
            self.following = following

    def apply_measured_pose(self, role, positions):
        import numpy as np
        import warp as wp
        from .robot import forward_kinematics, joint_limits
        limits=joint_limits(role)
        if role not in self.robots or set(positions)!=set(limits) or any(
            isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
            or not limits[n][0]<=v<=limits[n][1] for n,v in positions.items()):
            raise ValueError('Measured pose does not match the virtual articulation')
        bodies=self.robots[role]['bodies']
        values=self.state.body_q.numpy();base=values[bodies['base_link']]
        poses=forward_kinematics(role,positions,wp.transform(base[:3],base[3:]))
        for name,index in bodies.items():
            pose=poses[name];values[index]=np.asarray((*pose.p,*pose.q),dtype=np.float32)
        for state in (self.state,self.next_state):
            state.body_q.assign(values)
            velocity=state.body_qd.numpy()
            for index in bodies.values():velocity[index]=0
            state.body_qd.assign(velocity)
        self.targets[role]=dict(positions)

    def _update_targets(self):
        import numpy as np
        from .robot import follower_targets
        if self.following and 'leader' in self.robots and 'follower' in self.robots:
            self.targets['follower'] = follower_targets(self.robot_positions()['leader'])
        values = self.control.joint_target_q.numpy()
        for role,targets in self.targets.items():
            for name,value in targets.items():
                values[self.target_indices[role][name]] = value
        self.control.joint_target_q.assign(np.asarray(values,dtype='float32'))

    def world_matrices(self):
        from pxr import Gf
        poses = self.state.body_q.numpy()
        matrices = []
        for index in sorted(self.mapping.index_to_path):
            pose = poses[index]
            transform = Gf.Transform()
            transform.SetTranslation(Gf.Vec3d(*(float(x)/self.units for x in pose[:3])))
            transform.SetRotation(Gf.Rotation(Gf.Quatd(float(pose[6]), Gf.Vec3d(*map(float, pose[3:6])))))
            transform.SetScale(Gf.Vec3d(*self.scales[index]))
            matrices.append(transform.GetMatrix())
        return matrices

    def render_matrices(self):
        bodies = dict(zip(sorted(self.mapping.index_to_path), self.world_matrices()))
        result = []
        for index, (parent_index, offset) in zip(sorted(self.mapping.index_to_path), self._render_parents):
            parent = offset if parent_index is None else offset * bodies[parent_index]
            result.append(bodies[index] * parent.GetInverse())
        return result
