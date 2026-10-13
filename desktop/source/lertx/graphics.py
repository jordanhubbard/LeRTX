"""Select the native renderer backend without importing NVIDIA packages on Darwin."""
from __future__ import annotations

import sys


def backend() -> str:
    return "metal" if sys.platform == "darwin" else "ovrtx"


def ovrtx():
    if backend() == "metal":
        from . import metal_ovrtx
        return metal_ovrtx
    import ovrtx as module
    return module


def ovstage():
    if backend() == "metal":
        from . import metal_ovstage
        return metal_ovstage
    import ovstage as module
    return module


def physics_device(gpu_index: int = 0) -> str:
    if backend() == "metal":
        return "cpu"
    return f"cuda:{int(gpu_index)}"


def device_name(gpu_index: int = 0) -> str:
    if backend() == "metal":
        from . import metal_ovrtx
        return metal_ovrtx.device_name()
    import warp as wp
    return wp.get_device(physics_device(gpu_index)).name
