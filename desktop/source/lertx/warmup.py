"""Prepare native caches and verify a real frame during explicit installation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import time

from .config import DEFAULT_PROFILE
from .runtime import SceneWorker
from .scene import create_default_scene


def main():
    started = time.monotonic()
    # Windows first-install shader preparation exceeded the old five-minute
    # process limit on a supported L40. Reserve a minute of the parent's
    # fifteen-minute process budget for cleanup and interpreter shutdown.
    deadline = started + 840
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["rendering"].update(width=640, height=360)
    print("Preparing the NVIDIA renderer; first-install shader compilation may take up to 14 minutes.", flush=True)
    with tempfile.TemporaryDirectory(prefix="lertx-warmup-") as directory:
        scene = Path(directory) / "workspace.usda"
        create_default_scene(str(scene))
        worker = SceneWorker(profile)
        worker.start()
        try:
            worker.submit(lambda: worker.open_document(str(scene))).result(
                timeout=max(0, deadline - time.monotonic()))
            result = worker.submit(lambda: worker.tick(0)).result(
                timeout=max(0, deadline - time.monotonic()))
            frame = result["frame"]
            import numpy as np
            pixels = np.frombuffer(frame.data, dtype=frame.dtype_name).reshape(
                frame.height, frame.width, frame.channels)
            if frame.width != 640 or frame.height != 360 or float(pixels[..., :3].std()) < 5:
                raise RuntimeError("The renderer did not produce a meaningful native frame.")
        finally:
            worker.stop()
    print(json.dumps({"native_warmup": "passed", "cleanup_completed": True,
                      "seconds": round(time.monotonic() - started, 3)}), flush=True)


if __name__ == "__main__":
    main()
