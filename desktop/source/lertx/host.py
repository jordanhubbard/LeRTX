"""Host and interpreter support checks for native commands.

Native commands must reject an unsupported host or Python ABI with an
actionable error before any SDK initialization is attempted.
"""
from __future__ import annotations

import platform
import sys

_SUPPORTED_PYTHON = ((3, 11), (3, 12))
_SUPPORTED_MACHINES = {
    "linux": ("x86_64", "amd64", "aarch64", "arm64"),
    "win32": ("x86_64", "amd64"),
}
_SUPPORTED_PLATFORMS = ("linux", "win32")


class UnsupportedHostError(RuntimeError):
    """Raised when the current host or interpreter cannot run native features."""


def check_native_support() -> None:
    """Raise ``UnsupportedHostError`` when native execution is not possible here."""
    version = (sys.version_info.major, sys.version_info.minor)
    if version not in _SUPPORTED_PYTHON:
        raise UnsupportedHostError(
            "Native desktop execution requires CPython 3.11 or 3.12; "
            f"the running interpreter is {platform.python_version()}."
        )
    if sys.platform not in _SUPPORTED_PLATFORMS:
        raise UnsupportedHostError(
            "Native desktop execution requires Linux x86-64/ARM64 or Windows 11 x86-64; "
            f"the running platform is {sys.platform!r}."
        )
    machine = platform.machine().lower()
    if machine not in _SUPPORTED_MACHINES[sys.platform]:
        raise UnsupportedHostError(
            "Native desktop execution requires Linux x86-64/ARM64 or Windows 11 x86-64; "
            f"the running host is {sys.platform}/{platform.machine()}."
        )


def usd_distribution() -> str:
    """The one distribution providing pxr for this target's dependency closure."""
    if sys.platform == "linux" and platform.machine().lower() in ("aarch64", "arm64"):
        return "usd-exchange"
    return "usd-core"


def is_native_supported() -> bool:
    try:
        check_native_support()
    except UnsupportedHostError:
        return False
    return True
