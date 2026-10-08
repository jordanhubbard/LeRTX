"""Non-rendering installation diagnostics. This is not native acceptance."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import subprocess
import sys

from .host import check_native_support, usd_distribution


def report():
    problems = []
    try:
        check_native_support()
    except RuntimeError as error:
        problems.append(str(error))
    expected = {"ovrtx": "0.5.1.385782", "ovstage": "0.2.1.385922",
                "newton": "1.6.1", "warp-lang": "1.18.0",
                "numpy": "2.4.6" if sys.version_info < (3, 12) else "2.5.3",
                "PySide6": "6.12.0", "PySide6-Addons": "6.12.0",
                "PySide6-Essentials": "6.12.0", "shiboken6": "6.12.0", "pyserial": "3.5",
                "PySide6-Pdf": "6.12.0.140", "PySide6-WebEngine": "6.12.0.140",
                "lertx-robot-assets": "1.0.0"}
    provider = usd_distribution()
    expected[provider] = "3.0.1" if provider == "usd-exchange" else "26.8"
    installed = {}
    for name, version in expected.items():
        try:
            installed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            installed[name] = None
        if installed[name] != version:
            problems.append(f"{name}: expected {version}, found {installed[name] or 'missing'}")
    other = "usd-core" if provider == "usd-exchange" else "usd-exchange"
    try:
        importlib.metadata.version(other)
        problems.append(f"Conflicting USD distribution {other}; recreate the isolated environment.")
    except importlib.metadata.PackageNotFoundError:
        pass
    for module in ("pxr", "ovrtx", "ovstage", "newton", "warp", "PySide6", "serial"):
        if importlib.util.find_spec(module) is None:
            problems.append(f"Missing import: {module}")
    gpu = None
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version",
                                 "--format=csv,noheader"], capture_output=True,
                                text=True, timeout=15, check=True)
        gpu = result.stdout.strip()
        if not gpu:
            problems.append("NVIDIA driver returned no GPU.")
    except (OSError, subprocess.SubprocessError):
        problems.append("NVIDIA driver unavailable: nvidia-smi failed.")
    return {"ready_for_launch": not problems, "scope": "installation-preflight-not-rendering",
            "platform": platform.system(), "architecture": platform.machine(),
            "python": platform.python_version(), "packages": installed,
            "gpu": gpu, "problems": problems}


def main():
    result = report()
    print(json.dumps(result, indent=2))
    if not result["ready_for_launch"]:
        sys.exit(1)
