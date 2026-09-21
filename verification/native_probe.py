"""Independent SDK integration probe; not application implementation.

Creates an original USD fixture, renders it through OVRTX/OVStage, moves its
sphere with Newton, and checks the native image and pose evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import newton
import numpy as np
import ovrtx
import ovstage
import warp as wp
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdRender, UsdShade


def fixture(path: Path) -> None:
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    for name, position, scale, color in (
        ("Table", (0, 0, -0.05), (2, 2, 0.1), (0.16, 0.20, 0.25)),
        ("Obstacle", (0.4, 0.2, 0.15), (0.25, 0.25, 0.3), (0.12, 0.38, 0.48)),
    ):
        cube = UsdGeom.Cube.Define(stage, f"/World/{name}")
        cube.CreateSizeAttr(1.0)
        cube.AddTranslateOp().Set(Gf.Vec3d(*position))
        cube.AddScaleOp().Set(Gf.Vec3d(*scale))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        material(stage, cube.GetPrim(), name, color)
    ball = UsdGeom.Sphere.Define(stage, "/World/Probe")
    ball.CreateRadiusAttr(0.1)
    ball.AddTransformOp().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(0, 0, 0.8)))
    UsdPhysics.RigidBodyAPI.Apply(ball.GetPrim())
    UsdPhysics.CollisionAPI.Apply(ball.GetPrim())
    material(stage, ball.GetPrim(), "Probe", (0.95, 0.32, 0.08))
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.AddTransformOp().Set(
        Gf.Matrix4d().SetLookAt(
            Gf.Vec3d(1.7, -1.8, 1.4), Gf.Vec3d(0, 0, 0.25), Gf.Vec3d(0, 0, 1)
        ).GetInverse()
    )
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100))
    camera.CreateFocalLengthAttr(30)
    dome = UsdLux.DomeLight.Define(stage, "/World/Fill")
    dome.CreateIntensityAttr(250)
    light = UsdLux.DistantLight.Define(stage, "/World/Key")
    light.CreateIntensityAttr(1500)
    light.AddRotateXYZOp().Set(Gf.Vec3f(25, -35, 0))
    product = UsdRender.Product.Define(stage, "/Render/Camera")
    product.CreateResolutionAttr(Gf.Vec2i(640, 480))
    product.CreateCameraRel().SetTargets([camera.GetPath()])
    color = UsdRender.Var.Define(stage, "/Render/Camera/LdrColor")
    color.CreateSourceNameAttr("LdrColor")
    product.CreateOrderedVarsRel().SetTargets([color.GetPath()])
    settings = UsdRender.Settings.Define(stage, "/Render/Settings")
    settings.CreateProductsRel().SetTargets([product.GetPath()])
    stage.SetMetadata("renderSettingsPrimPath", "/Render/Settings")
    stage.GetRootLayer().Save()


def material(stage, prim, name, rgb):
    mat = UsdShade.Material.Define(stage, f"/World/Materials/{name}")
    shader = UsdShade.Shader.Define(stage, mat.GetPath().AppendChild("Surface"))
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def render(renderer, ordinal, path):
    pixels = None
    # A short convergence warmup makes comparisons independent of shader startup.
    for _ in range(8):
        products = renderer.step(
            render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=ordinal
        )
        for product in products.values():
            for frame in product.frames:
                mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
                view = np.from_dlpack(mapped)
                pixels = view.copy()
                del view
                mapped.unmap()
                del mapped
        del products
    if pixels is None or pixels.shape[:2] != (480, 640):
        raise AssertionError("renderer did not produce a 640x480 frame")
    if not np.isfinite(pixels).all() or float(pixels[..., :3].std()) < 5:
        raise AssertionError("frame contains no meaningful image variation")
    Image.fromarray(pixels).save(path)
    return pixels


def probe(output: Path):
    output.mkdir(parents=True, exist_ok=False)
    usd_path = output / "workspace.usda"
    fixture(usd_path)
    wp.init()
    builder = newton.ModelBuilder()
    body = builder.add_body(
        xform=wp.transform(wp.vec3(0, 0, 0.8), wp.quat_identity()), label="/World/Probe"
    )
    builder.add_shape_sphere(body, radius=0.1)
    builder.add_ground_plane()
    model = builder.finalize(device="cuda:0")
    state, next_state = model.state(), model.state()
    control = model.control()
    solver = newton.solvers.SolverXPBD(model)
    collision_pipeline = newton.CollisionPipeline(model)
    contacts = collision_pipeline.contacts()
    initial = state.body_q.numpy()[body].copy()
    renderer, stage = None, None
    try:
        print("Creating OVRTX renderer", flush=True)
        renderer = ovrtx.Renderer()
        stage = ovstage.Stage("lertx.sdk-probe")
        renderer.attach_ovstage(stage)
        ovstage.population.open_usd(stage, str(usd_path.resolve()), ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        before = render(renderer, 1, output / "before.png")
        print("Stepping Newton on CUDA", flush=True)
        for _ in range(240):
            state.clear_forces()
            collision_pipeline.collide(state, contacts)
            solver.step(state, next_state, control, contacts, 1 / 240)
            state, next_state = next_state, state
        final = state.body_q.numpy()[body].copy()
        if not (initial[2] - final[2] > 0.5 and 0.075 < final[2] < 0.125):
            raise AssertionError(f"sphere did not fall and settle: {initial[2]} -> {final[2]}")
        paths = ovstage.PathDictionary(stage)
        path_list = paths.create_path_list_from_strings(["/World/Probe"])
        query = stage.query_from_path_list(path_list)
        quat = Gf.Quatd(float(final[6]), Gf.Vec3d(*map(float, final[3:6])))
        matrix = Gf.Matrix4d().SetRotate(Gf.Rotation(quat))
        matrix.SetTranslateOnly(Gf.Vec3d(*map(float, final[:3])))
        transforms = np.array([matrix], dtype=np.float64)
        stage.write_attribute(
            query, paths.intern_token("omni:xform"), ordinal=2,
            tensors=transforms, is_array=False,
        ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        after = render(renderer, 2, output / "after.png")
        difference = float(np.abs(before.astype(float) - after.astype(float)).mean())
        if difference < 0.2:
            raise AssertionError("Newton pose did not change the rendered frame")
        result = {
            "passed": True, "initial_pose": initial.tolist(), "final_pose": final.tolist(),
            "mean_image_difference": difference, "frames": {},
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "system": {"os": platform.system(), "architecture": platform.machine(),
                       "python": platform.python_version()},
            "gpu": subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True, timeout=15,
            ).stdout.strip(),
            "packages": {name: importlib.metadata.version(name) for name in (
                "ovrtx", "ovstage", "newton", "warp-lang", "numpy", "usd-core"
            )},
        }
        for name in ("before.png", "after.png", "workspace.usda"):
            result["frames"][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    finally:
        if renderer is not None:
            if stage is not None:
                renderer.detach_ovstage()
                stage.destroy()
            renderer.destroy()
    # A successful frame is not a successful lifecycle until cleanup returns.
    result["cleanup_completed"] = True
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    probe(parser.parse_args().output)
