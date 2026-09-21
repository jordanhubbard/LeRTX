"""USD authoring and native (OVRTX/OVStage/Newton) scene coordination.

Every native SDK import in this module is deliberately lazy (performed
inside functions/methods, never at import time) so that portable commands
such as ``defaults`` and ``validate-settings`` never touch Qt or a GPU.
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


class SimulationDisabledError(RuntimeError):
    """Raised when an authored prim cannot be simulated and identifies it."""


def create_default_scene(usd_path: str) -> None:
    """Author an original metric Z-up default scene at ``usd_path``.

    Contains a work surface, a static box obstacle, a dynamic orange
    sphere above the surface, a perspective camera and illumination.
    """
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

    stage = Usd.Stage.CreateNew(usd_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    surface = UsdGeom.Cube.Define(stage, "/World/WorkSurface")
    surface.CreateSizeAttr(1.0)
    surface_xform = UsdGeom.Xformable(surface)
    surface_xform.AddScaleOp().Set(Gf.Vec3f(2.0, 2.0, 0.05))
    surface_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.025))
    UsdPhysics.CollisionAPI.Apply(surface.GetPrim())

    obstacle = UsdGeom.Cube.Define(stage, "/World/Obstacle")
    obstacle.CreateSizeAttr(1.0)
    obstacle_xform = UsdGeom.Xformable(obstacle)
    obstacle_xform.AddScaleOp().Set(Gf.Vec3f(0.2, 0.2, 0.2))
    obstacle_xform.AddTranslateOp().Set(Gf.Vec3d(0.4, 0.0, 0.1))
    UsdPhysics.CollisionAPI.Apply(obstacle.GetPrim())

    sphere = UsdGeom.Sphere.Define(stage, "/World/DynamicSphere")
    sphere.CreateRadiusAttr(0.08)
    sphere_xform = UsdGeom.Xformable(sphere)
    sphere_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.5))
    UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(sphere.GetPrim())

    material = UsdShade.Material.Define(stage, "/World/Looks/OrangeSphere")
    shader = UsdShade.Shader.Define(stage, "/World/Looks/OrangeSphere/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0.9, 0.45, 0.05)
    )
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(sphere.GetPrim()).Bind(material)

    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    eye = Gf.Vec3d(1.6, -1.6, 1.2)
    center = Gf.Vec3d(0.0, 0.0, 0.2)
    up = Gf.Vec3d(0.0, 0.0, 1.0)
    world_transform = Gf.Matrix4d().SetLookAt(eye, center, up).GetInverse()
    UsdGeom.Xformable(camera).AddTransformOp().Set(world_transform)

    dome = UsdLux.DomeLight.Define(stage, "/World/Lights/Dome")
    dome.CreateIntensityAttr(1000.0)
    key_light = UsdLux.DistantLight.Define(stage, "/World/Lights/Key")
    key_light.CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(key_light).AddRotateXYZOp().Set(Gf.Vec3f(-35.0, 25.0, 0.0))

    ensure_render_product(stage, camera_path="/World/Camera", width=1280, height=720)

    stage.GetRootLayer().Save()


def ensure_render_product(stage, camera_path: str, width: int, height: int) -> str:
    """Ensure the stage has a render product/settings referencing ``camera_path``.

    Safe to call on a user-opened scene: writes only to the current edit
    target (a runtime/session layer when opening user scenes), never as a
    destructive change to the user's authored source file.
    """
    from pxr import Sdf, Usd, UsdRender

    product_path = "/Render/Product"
    settings_path = "/Render/Settings"
    var_path = "/Render/Vars/LdrColor"

    render_var = UsdRender.Var.Define(stage, var_path)
    render_var.CreateSourceNameAttr("LdrColor")
    render_var.CreateDataTypeAttr("color3f")

    product = UsdRender.Product.Define(stage, product_path)
    product.CreateCameraRel().SetTargets([Sdf.Path(camera_path)])
    product.CreateResolutionAttr((int(width), int(height)))
    product.CreateOrderedVarsRel().SetTargets([Sdf.Path(var_path)])

    settings = UsdRender.Settings.Define(stage, settings_path)
    settings.CreateProductsRel().SetTargets([Sdf.Path(product_path)])

    stage.SetMetadata("renderSettingsPrimPath", settings_path)
    return product_path


@dataclass
class BodyMapping:
    """Maps Newton rigid-body indices to their originating USD prim paths."""

    index_to_path: dict = field(default_factory=dict)

    def add(self, body_index: int, prim_path: str) -> None:
        self.index_to_path[body_index] = prim_path

    def paths_in_index_order(self) -> list:
        return [self.index_to_path[i] for i in sorted(self.index_to_path)]


def build_newton_model(stage, up_axis: str = "Z", gravity: float = -9.81):
    """Construct a Newton model from supported rigid bodies on ``stage``.

    Returns ``(builder, mapping)``. Any prim with unsupported collision
    geometry, nonuniform sphere scale, shear, or nested rigid bodies is
    reported via ``SimulationDisabledError`` naming the affected prim path,
    and physics stays disabled for that scene rather than approximating it.
    """
    import newton
    import warp as wp
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    builder = newton.ModelBuilder(up_axis=up_axis, gravity=gravity)
    mapping = BodyMapping()

    for prim in stage.Traverse():
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            continue
        xformable = UsdGeom.Xformable(prim)
        world_matrix = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        translation = world_matrix.ExtractTranslation()
        rotation = world_matrix.ExtractRotationQuat()
        body_index = builder.add_body(
            xform=wp.transform(
                (translation[0], translation[1], translation[2]),
                (
                    rotation.GetImaginary()[0],
                    rotation.GetImaginary()[1],
                    rotation.GetImaginary()[2],
                    rotation.GetReal(),
                ),
            ),
            label=str(prim.GetPath()),
        )
        mapping.add(body_index, str(prim.GetPath()))

        if UsdGeom.Sphere(prim):
            scale = world_matrix.ExtractScale() if hasattr(world_matrix, "ExtractScale") else Gf.Vec3d(1, 1, 1)
            if abs(scale[0] - scale[1]) > 1e-6 or abs(scale[1] - scale[2]) > 1e-6:
                raise SimulationDisabledError(
                    f"nonuniform sphere scale on {prim.GetPath()}; physics disabled for this scene"
                )
            radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get() or 0.5
            builder.add_shape_sphere(body_index, radius=radius * scale[0])
        elif UsdGeom.Cube(prim):
            size = UsdGeom.Cube(prim).GetSizeAttr().Get() or 1.0
            scale = world_matrix.ExtractScale() if hasattr(world_matrix, "ExtractScale") else Gf.Vec3d(1, 1, 1)
            builder.add_shape_box(
                body_index,
                hx=size * scale[0] / 2.0,
                hy=size * scale[1] / 2.0,
                hz=size * scale[2] / 2.0,
            )
        else:
            raise SimulationDisabledError(
                f"unsupported collider geometry on {prim.GetPath()}; physics disabled for this scene"
            )

    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.CollisionAPI) and not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            xformable = UsdGeom.Xformable(prim)
            world_matrix = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            translation = world_matrix.ExtractTranslation()
            if UsdGeom.Cube(prim):
                size = UsdGeom.Cube(prim).GetSizeAttr().Get() or 1.0
                scale = world_matrix.ExtractScale() if hasattr(world_matrix, "ExtractScale") else Gf.Vec3d(1, 1, 1)
                builder.add_shape_box(
                    -1,
                    hx=size * scale[0] / 2.0,
                    hy=size * scale[1] / 2.0,
                    hz=size * scale[2] / 2.0,
                    xform=wp.transform((translation[0], translation[1], translation[2]), (0.0, 0.0, 0.0, 1.0)),
                )

    return builder, mapping


@dataclass
class Frame:
    """An owned (copied) RGB(A) frame ready for Qt delivery."""

    width: int
    height: int
    channels: int
    dtype_name: str
    data: bytes


class NativeWorker:
    """Owns all OVRTX/OVStage/Newton state and runs it on one dedicated thread.

    A bounded command queue and a single owned latest-frame slot keep the
    worker responsive; it never runs an unbounded slot that starves queued
    stop/control commands.
    """

    def __init__(self, gpu_index: int = 0, queue_size: int = 8) -> None:
        self._gpu_index = gpu_index
        self._commands: "queue.Queue" = queue.Queue(maxsize=queue_size)
        self._latest_frame_lock = threading.Lock()
        self._latest_frame: Optional[Frame] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_error: Optional[Callable[[Exception], None]] = None
        self._renderer = None
        self._stage = None
        self._ordinal = 0

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        self._on_error = handler

    def start(self) -> None:
        from lertx import host

        host.check_native_support()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="lertx-native-worker", daemon=True)
        self._thread.start()

    def submit(self, command: Callable[[], None]) -> None:
        self._commands.put(command)

    def latest_frame(self) -> Optional[Frame]:
        with self._latest_frame_lock:
            return self._latest_frame

    def stop(self) -> None:
        self._stop_event.set()
        self._commands.put(None)
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _set_latest_frame(self, frame: Frame) -> None:
        with self._latest_frame_lock:
            self._latest_frame = frame

    def _run(self) -> None:
        try:
            self._initialize()
            while not self._stop_event.is_set():
                command = self._commands.get()
                if command is None:
                    break
                command()
        except Exception as exc:  # noqa: BLE001 - propagate to UI, then clean up
            if self._on_error is not None:
                self._on_error(exc)
        finally:
            self._cleanup()

    def _initialize(self) -> None:
        import ovrtx
        import ovstage

        config = ovrtx.RendererConfig(active_cuda_gpus=str(self._gpu_index))
        self._renderer = ovrtx.Renderer(config=config)
        self._stage = ovstage.Stage("lertx-runtime-stage")
        self._renderer.attach_ovstage(self._stage)

    def open_usd(self, absolute_usd_path: str) -> None:
        import ovstage

        self._ordinal += 1
        ovstage.population.open_usd(self._stage, absolute_usd_path, ordinal=self._ordinal)
        self._stage.advance_write_floor(self._ordinal, ovstage.Scope.ALL).wait()

    def publish_transforms(self, mapping: BodyMapping, matrices) -> None:
        import numpy as np
        import ovstage

        paths = ovstage.PathDictionary(self._stage)
        path_list = paths.create_path_list_from_strings(mapping.paths_in_index_order())
        query = self._stage.query_from_path_list(path_list)
        matrix_array = np.asarray(matrices, dtype=np.float64)
        if matrix_array.size == 0:
            return
        self._ordinal += 1
        self._stage.write_attribute(
            query,
            paths.intern_token("omni:xform"),
            ordinal=self._ordinal,
            tensors=matrix_array,
            is_array=False,
        ).wait()
        self._stage.advance_write_floor(self._ordinal, ovstage.Scope.ALL).wait()

    def render(self, product_path: str, delta_time: float, var_path: str = "/Render/Vars/LdrColor") -> Frame:
        import ovrtx

        products = self._renderer.step(
            render_products={product_path}, delta_time=delta_time, ordinal=self._ordinal
        )
        for product in products.values():
            for frame in product.frames:
                mapped = frame.render_vars[var_path].map(device=ovrtx.Device.CPU)
                try:
                    import numpy as np

                    view = np.from_dlpack(mapped)
                    owned = np.array(view, copy=True)
                finally:
                    mapped.unmap()
                result = Frame(
                    width=owned.shape[1],
                    height=owned.shape[0],
                    channels=owned.shape[2] if owned.ndim > 2 else 1,
                    dtype_name=str(owned.dtype),
                    data=owned.tobytes(),
                )
                self._set_latest_frame(result)
                return result
        raise RuntimeError("renderer.step produced no frame for the requested product")

    def _cleanup(self) -> None:
        if self._stage is not None:
            try:
                if self._renderer is not None:
                    self._renderer.detach_ovstage()
                self._stage.destroy()
            finally:
                self._stage = None
        if self._renderer is not None:
            try:
                self._renderer.destroy()
            finally:
                self._renderer = None
