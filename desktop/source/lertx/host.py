"""Host and interpreter support checks for native commands.

Native commands must reject an unsupported host or Python ABI with an
actionable error before any SDK initialization is attempted.
"""
from __future__ import annotations

import platform
import sys

_SUPPORTED_PYTHON = ((3, 11), (3, 12))
_SUPPORTED_MACHINES = ("x86_64", "amd64")
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
            "Native desktop execution requires Linux x86-64 or Windows x86-64; "
            f"the running platform is {sys.platform!r}."
        )
    machine = platform.machine().lower()
    if machine not in _SUPPORTED_MACHINES:
        raise UnsupportedHostError(
            "Native desktop execution requires an x86-64 host; "
            f"the running machine is {platform.machine()!r}."
        )


def is_native_supported() -> bool:
    try:
        check_native_support()
    except UnsupportedHostError:
        return False
    return True
