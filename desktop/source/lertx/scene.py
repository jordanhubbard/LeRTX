"""USD authoring and native (OVRTX/OVStage/Newton) scene coordination.

Every native SDK import in this module is deliberately lazy (performed
inside functions/methods, never at import time) so that portable commands
such as ``defaults`` and ``validate-settings`` never touch Qt or a GPU.
"""
from __future__ import annotations

import queue
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Callable, Optional


class SimulationDisabledError(RuntimeError):
    """Raised when an authored prim cannot be simulated and identifies it."""


def create_default_scene(usd_path: str, *, include_robots=False) -> None:
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
    surface_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.025))
    surface_xform.AddScaleOp().Set(Gf.Vec3f(2.0, 2.0, 0.05))
    UsdPhysics.CollisionAPI.Apply(surface.GetPrim())

    obstacle = UsdGeom.Cube.Define(stage, "/World/Obstacle")
    obstacle.CreateSizeAttr(1.0)
    obstacle_xform = UsdGeom.Xformable(obstacle)
    obstacle_xform.AddTranslateOp().Set(Gf.Vec3d(0.4, 0.0, 0.1))
    obstacle_xform.AddScaleOp().Set(Gf.Vec3f(0.2, 0.2, 0.2))
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

    if include_robots:
        from .robot import author_pair
        obstacle_xform.GetOrderedXformOps()[0].Set(Gf.Vec3d(.65, .45, .1))
        sphere_xform.GetOrderedXformOps()[0].Set(Gf.Vec3d(0, .45, .5))
        author_pair(stage)
    stage.GetRootLayer().Save()


def ensure_render_product(stage, camera_path: str, width: int, height: int, quality="balanced") -> str:
    """Ensure the stage has a render product/settings referencing ``camera_path``.

    Safe to call on a user-opened scene: writes only to the current edit
    target (a runtime/session layer when opening user scenes), never as a
    destructive change to the user's authored source file.
    """
    from pxr import Gf, Sdf, Usd, UsdRender

    product_path = "/Render/Product"
    settings_path = "/Render/Settings"
    var_path = "/Render/Vars/LdrColor"

    render_var = UsdRender.Var.Define(stage, var_path)
    render_var.CreateSourceNameAttr("LdrColor")
    render_var.CreateDataTypeAttr("color3f")

    product = UsdRender.Product.Define(stage, product_path)
    product.CreateCameraRel().SetTargets([Sdf.Path(camera_path)])
    product.CreateResolutionAttr(Gf.Vec2i(int(width), int(height)))
    product.CreateOrderedVarsRel().SetTargets([Sdf.Path(var_path)])
    if quality not in ("balanced", "high"):
        raise ValueError("Unsupported rendering quality")
    # Pinned OVRTX generatedSchema.usda: OmniRtxSettingsRtAPI_1's DLSS token.
    product.GetPrim().AddAppliedSchema("OmniRtxSettingsRtAPI_1")
    product.GetPrim().CreateAttribute("omni:rtx:post:dlss:execMode",
        Sdf.ValueTypeNames.Token, custom=False).Set("quality" if quality == "high" else "balanced")

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


def build_newton_model(stage, up_axis=None, gravity=-9.81):
    """Compatibility entry point; authored USD defines units and up axis."""
    from .physics import build_model
    builder, mapping, _scales, _units = build_model(stage, gravity)
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
        if self._thread is not None:
            raise RuntimeError("Native worker already started")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="lertx-native-worker", daemon=True)
        self._thread.start()

    def submit(self, command: Callable[[], None]) -> Future:
        future = Future()
        if self._stop_event.is_set() or self._thread is None or not self._thread.is_alive():
            future.set_exception(RuntimeError("Native worker is stopped"))
            return future
        try:
            self._commands.put_nowait((command, future))
        except queue.Full:
            future.set_exception(RuntimeError("Native worker command queue is full"))
        return future

    def latest_frame(self) -> Optional[Frame]:
        with self._latest_frame_lock:
            return self._latest_frame

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                raise TimeoutError("Native worker is still finishing GPU work")
            self._thread = None

    def _set_latest_frame(self, frame: Frame) -> None:
        with self._latest_frame_lock:
            self._latest_frame = frame

    def _run(self) -> None:
        try:
            self._initialize()
            while not self._stop_event.is_set():
                try:
                    command, future = self._commands.get(timeout=0.05)
                except queue.Empty:
                    continue
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    future.set_result(command())
                except (ValueError, OSError) as exc:
                    # User input / filesystem failures are recoverable commands.
                    # Return them to the UI without destroying a usable scene.
                    future.set_exception(exc)
                except Exception as exc:
                    future.set_exception(exc)
                    raise
        except Exception as exc:  # noqa: BLE001 - propagate to UI, then clean up
            if self._on_error is not None:
                self._on_error(exc)
        finally:
            self._stop_event.set()
            try:
                self._cleanup()
            finally:
                while True:
                    try:
                        _, future = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    if not future.done():
                        future.set_exception(RuntimeError("Native worker stopped before command execution"))

    def _initialize(self) -> None:
        # The pinned native stack is import-order sensitive. Load authored USD
        # before RTX loads its native dependencies, including in fresh processes
        # opening an existing file (where no default scene was authored first).
        from pxr import Usd
        # Import alone leaves USD's stage/plugin initialization lazy. Exercise
        # that initialization before RTX attachment, also for existing-file
        # launches which do not author the default fixture first.
        usd_bootstrap = Usd.Stage.CreateInMemory()
        if usd_bootstrap is None:
            raise RuntimeError("Could not initialize OpenUSD")
        del usd_bootstrap
        import ovrtx
        import ovstage

        # The SDK otherwise retains its backend after Renderer.destroy().
        # The worker owns that lifetime too: closing must release native work,
        # not leave a process-global rendering system alive until interpreter exit.
        config = ovrtx.RendererConfig(active_cuda_gpus=str(self._gpu_index),
                                      selection_outline_enabled=True,
                                      selection_outline_width=3,
                                      keep_system_alive=False)
        self._renderer = ovrtx.Renderer(config=config)
        self._renderer.set_selection_group_styles({1: ovrtx.SelectionGroupStyle(
            outline_color=(1., .65, .1, 1.), fill_color=(0., 0., 0., 0.))})
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

        matrix_array = np.asarray(matrices, dtype=np.float64)
        if matrix_array.size == 0:
            return
        # OVStage stores one matrix-valued element per prim. A plain N x 4 x 4
        # scalar tensor can be misinterpreted as a different attribute column.
        tensor = ovstage.make_dltensor(
            matrix_array.reshape(-1, 16),
            dtype=ovstage.DLDataType(code=ovstage.DLDataTypeCode.kDLFloat, bits=64, lanes=16),
            shape=[len(matrix_array)],
        )
        paths = ovstage.PathDictionary(self._stage)
        with paths.create_path_list_from_strings(mapping.paths_in_index_order()) as path_list:
            with self._stage.query_from_path_list(path_list) as query:
                self._ordinal += 1
                self._stage.write_attribute(
                    query, paths.intern_token("omni:xform"), ordinal=self._ordinal,
                    tensors=tensor, is_array=False,
                    semantic=ovstage.AttributeSemantic.MATRIX,
                    prim_mode=ovstage.PrimMode.UPSERT,
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
                view = None
                try:
                    import numpy as np

                    view = np.from_dlpack(mapped)
                    owned = np.array(view, copy=True)
                finally:
                    del view
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
        renderer, stage = self._renderer, self._stage
        self._renderer = self._stage = None
        try:
            if renderer is not None and stage is not None:
                renderer.detach_ovstage()
        finally:
            try:
                if stage is not None:
                    stage.destroy()
            finally:
                if renderer is not None:
                    renderer.destroy()
