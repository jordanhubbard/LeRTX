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
    for prim in stage.Traverse():
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
    return builder, mapping, scales, units


class PhysicsScene:
    def __init__(self, stage, device="cuda:0", gravity=-9.81):
        import newton
        builder, self.mapping, self.scales, self.units = build_model(stage, gravity)
        if not self.mapping.index_to_path:
            raise SimulationDisabledError("No supported rigid bodies; physics disabled")
        self.model = builder.finalize(device=device)
        self.state, self.next_state = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.solver = newton.solvers.SolverXPBD(self.model)
        self.pipeline = newton.CollisionPipeline(self.model)
        self.contacts = self.pipeline.contacts()
        self.time = 0.0

    def step(self, dt, substeps=1):
        if not math.isfinite(dt) or dt <= 0 or not 1 <= substeps <= 64:
            raise ValueError("Invalid physics step")
        for _ in range(substeps):
            self.state.clear_forces()
            self.pipeline.collide(self.state, self.contacts)
            self.solver.step(self.state, self.next_state, self.control, self.contacts, dt/substeps)
            self.state, self.next_state = self.next_state, self.state
        self.time += dt

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
