"""Independent native SDK coupling probe using an exact retained USD fixture.

This does not import a USD authoring package, implement the application, or prove
editing/UI behavior. The fixture and single nonrotating body's mapping are fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path

import newton
import numpy as np
import ovrtx
import ovstage
import warp as wp
from PIL import Image

FIXTURE_SHA256 = "686dc2824a1a798ade70756ccc49287821b1b7767529c2a3ea5cef0b89bf188c"


def render(renderer, ordinal: int, destination: Path):
    pixels = None
    for _ in range(8):
        products = renderer.step(
            render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=ordinal
        )
        for product in products.values():
            for frame in product.frames:
                mapped = frame.render_vars["/Render/Camera/LdrColor"].map(
                    device=ovrtx.Device.CPU
                )
                view = None
                try:
                    view = np.from_dlpack(mapped)
                    pixels = view.copy()
                finally:
                    del view
                    mapped.unmap()
    if pixels is None or pixels.shape[:2] != (480, 640):
        raise AssertionError("No native 640x480 frame")
    if not np.isfinite(pixels).all() or float(pixels[..., :3].std()) < 5:
        raise AssertionError("Native frame lacks meaningful variation")
    Image.fromarray(pixels).save(destination)
    return pixels


def probe(fixture: Path, output: Path) -> None:
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != FIXTURE_SHA256:
        raise ValueError("Input is not the exact independently verified USD fixture")
    output.mkdir(parents=True, exist_ok=False)
    scene = output / "workspace.usda"
    shutil.copyfile(fixture, scene)
    wp.init()
    builder = newton.ModelBuilder()
    body = builder.add_body(
        xform=wp.transform(wp.vec3(0, 0, 0.8), wp.quat_identity()),
        label="/World/Probe",
    )
    builder.add_shape_sphere(body, radius=0.1)
    builder.add_ground_plane()
    model = builder.finalize(device="cuda:0")
    state, next_state = model.state(), model.state()
    control = model.control()
    solver = newton.solvers.SolverXPBD(model)
    pipeline = newton.CollisionPipeline(model)
    contacts = pipeline.contacts()
    initial = state.body_q.numpy()[body].copy()
    renderer, stage, attached = None, None, False
    try:
        print("Creating renderer and loading retained USD fixture", flush=True)
        renderer = ovrtx.Renderer()
        stage = ovstage.Stage("lertx.retained-fixture-probe")
        renderer.attach_ovstage(stage)
        attached = True
        ovstage.population.open_usd(stage, str(scene.resolve()), ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        before = render(renderer, 1, output / "before.png")
        print("Stepping mapped Newton body on CUDA", flush=True)
        for _ in range(240):
            state.clear_forces()
            pipeline.collide(state, contacts)
            solver.step(state, next_state, control, contacts, 1 / 240)
            state, next_state = next_state, state
        final = state.body_q.numpy()[body].copy()
        if not (initial[2] - final[2] > 0.5 and 0.075 < final[2] < 0.125):
            raise AssertionError("Newton body did not fall and settle")
        # This fixture exercises translation only. Refuse rotations instead of
        # claiming a general USD transform/parent/unit conversion implementation.
        if not np.allclose(final[3:], [0, 0, 0, 1], atol=1e-6):
            raise AssertionError("Fixed fixture unexpectedly rotated")
        transforms = np.eye(4, dtype=np.float64)[None, ...]
        transforms[0, 3, :3] = final[:3]
        paths = ovstage.PathDictionary(stage)
        selected = paths.create_path_list_from_strings(["/World/Probe"])
        query = stage.query_from_path_list(selected)
        stage.write_attribute(
            query,
            paths.intern_token("omni:xform"),
            ordinal=2,
            tensors=transforms,
            is_array=False,
        ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        after = render(renderer, 2, output / "after.png")
        difference = float(np.abs(before.astype(float) - after.astype(float)).mean())
        if difference < 0.2:
            raise AssertionError("Published Newton pose did not change native frames")
        result = {
            "passed": True,
            "scope": "fixed-fixture SDK coupling; not USD authoring or application acceptance",
            "initial_pose": initial.tolist(),
            "final_pose": final.tolist(),
            "body_prim": {"body_index": body, "prim_path": "/World/Probe"},
            "mean_image_difference": difference,
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "system": {
                "os": platform.system(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "gpu": subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            ).stdout.strip(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in (
                    "ovrtx",
                    "ovstage",
                    "newton",
                    "warp-lang",
                    "numpy",
                    "Pillow",
                )
            },
        }
    finally:
        try:
            if attached:
                renderer.detach_ovstage()
        finally:
            try:
                if stage is not None:
                    stage.destroy()
            finally:
                if renderer is not None:
                    renderer.destroy()
    result["cleanup_completed"] = True
    result["frames"] = {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest()
        for name in ("workspace.usda", "before.png", "after.png")
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    probe(arguments.fixture, arguments.output)
