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

    host.check_native_support()

    config_path = os.path.join(config.user_config_dir(), "settings.json")
    profile = config.load_profile(config_path)

    if scene_path is None:
        scene_path = os.path.join(tempfile.gettempdir(), "lertx-default-scene.usda")
        scene_module.create_default_scene(scene_path)

    application = ui_module.build_application()
    window = ui_module.build_main_window(
        profile,
        lambda: scene_module.NativeWorker(profile["rendering"]["device"]),
        scene_path,
        config_path,
    )
    window.show()
    window.open_scene(scene_path)
    application.exec()

    return {"application": "LeRTX", "closed": True}
