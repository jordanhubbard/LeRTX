"""Application entrypoint logic: command dispatch for ``main(payload)``.

Only ``defaults`` and ``validate-settings`` are guaranteed portable; they
never import Qt or a native SDK. ``launch`` requires a supported native
host and opens the real desktop application.
"""
from __future__ import annotations

import copy
import os
import tempfile
from typing import Any

from lertx import config

_COMMAND_ALLOWED_FIELDS = {
    "defaults": {"command"},
    "validate-settings": {"command", "profile"},
    "launch": {"command", "scene"},
}


def _reject_unknown_fields(payload: dict, allowed: set) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))


def main(payload: Any) -> dict:
    """Dispatch one application command. Accepts exactly one object argument."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "command" not in payload:
        raise ValueError("missing required field: command")
    command = payload["command"]
    if not isinstance(command, str):
        raise ValueError("command must be a string")
    if command not in _COMMAND_ALLOWED_FIELDS:
        raise ValueError(f"unknown command: {command}")

    _reject_unknown_fields(payload, _COMMAND_ALLOWED_FIELDS[command])

    if command == "defaults":
        return copy.deepcopy(config.DEFAULT_PROFILE)

    if command == "validate-settings":
        if "profile" not in payload:
            raise ValueError("missing required field: profile")
        return config.validate_profile(payload["profile"])

    scene_path = payload.get("scene")
    if scene_path is not None and not isinstance(scene_path, str):
        raise ValueError("scene must be a string")
    return _launch(scene_path)


def _launch(scene_path: Any) -> dict:
    from lertx import host, scene as scene_module, ui as ui_module
    from lertx.runtime import SceneWorker

    host.check_native_support()

    config_path = os.path.join(config.user_config_dir(), "settings.json")
    profile = config.load_profile(config_path)

    temporary = tempfile.TemporaryDirectory(prefix="lertx-workspace-") if scene_path is None else None
    window = None
    diagnostics = None
    from .device_control import DeviceRegistry
    devices = DeviceRegistry()
    try:
        if temporary:
            scene_path = os.path.join(temporary.name, "untitled.usda")
            scene_module.create_default_scene(scene_path, include_robots=True)
        application = ui_module.build_application()
        window = ui_module.build_main_window(
            profile, lambda: SceneWorker(profile), scene_path, config_path, device_registry=devices,
        )
        if os.environ.get('LERTX_DEBUG') == '1':
            from .live_debug import Diagnostics
            diagnostics = Diagnostics(window)
            window.diagnostics = diagnostics
        window.requires_save_as = temporary is not None
        window.show()
        window.open_scene(scene_path)
        application.exec()
        if window.worker is not None:
            window.worker.stop()
            window.worker = None
        return {"application": "LeRTX", "closed": True}
    finally:
        if diagnostics:
            diagnostics.close()
        devices.shutdown()
        if not devices.wait_closed():
            import logging
            logging.error("Device shutdown did not complete before application exit")
        if window is not None and window.worker is not None:
            window.worker.stop()
        if temporary:
            temporary.cleanup()
