"""Portable configuration: default profile and profile validation.

No network, native SDK, or GPU access happens anywhere in this module.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlsplit

DEFAULT_PROFILE: dict = {
    "llm": {
        "endpoint": "https://inference-api.nvidia.com/v1/responses",
        "model": "azure/openai/gpt-6-astra",
        "api_key": "",
        "max_output_tokens": 512,
        "timeout_seconds": 60,
        "remember_key": False,
    },
    "general": {
        "theme": "dark",
        "display_units": "m",
    },
    "rendering": {
        "device": 0,
        "width": 1280,
        "height": 720,
        "target_fps": 30,
        "quality": "balanced",
    },
    "physics": {
        "timestep_hz": 240,
        "substeps": 4,
        "gravity_m_s2": "-9.81",
        "reset_on_edit": True,
    },
    "devices": {
        "discovery_enabled": False,
        "telemetry_hz": 30,
        "actuation_enabled": False,
    },
    "workspace": {
        "asset_search_paths": [],
        "reconstruction_status": "unverified",
    },
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_str(value: Any) -> bool:
    return isinstance(value, str)


def _validate_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and len(value) > 0


def _validate_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _validate_literal_false(value: Any) -> bool:
    return value is False


def _validate_enum(values: tuple) -> Callable[[Any], bool]:
    def _check(value: Any) -> bool:
        return isinstance(value, str) and value in values

    return _check


def _validate_int_range(low: int, high: int) -> Callable[[Any], bool]:
    def _check(value: Any) -> bool:
        return _is_int(value) and low <= value <= high

    return _check


def _validate_int_min(low: int) -> Callable[[Any], bool]:
    def _check(value: Any) -> bool:
        return _is_int(value) and value >= low

    return _check


def _validate_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


_CREDENTIAL_QUERY_MARKERS = ("key", "token", "secret", "password", "auth", "credential")


def _validate_endpoint(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        return False
    if not parsed.netloc or "@" in parsed.netloc:
        return False
    if parsed.fragment:
        return False
    if parsed.query:
        lowered = parsed.query.lower()
        if any(marker in lowered for marker in _CREDENTIAL_QUERY_MARKERS):
            return False
    return True


def _validate_gravity(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, ValueError):
        return False
    return decimal_value.is_finite()


FIELDS: dict = {
    "llm": {
        "endpoint": _validate_endpoint,
        "model": _validate_nonempty_str,
        "api_key": _validate_str,
        "max_output_tokens": _validate_int_range(1, 131072),
        "timeout_seconds": _validate_int_range(1, 300),
        "remember_key": _validate_literal_false,
    },
    "general": {
        "theme": _validate_enum(("dark", "light")),
        "display_units": _validate_enum(("m", "cm", "mm")),
    },
    "rendering": {
        "device": _validate_int_min(0),
        "width": _validate_int_min(1),
        "height": _validate_int_min(1),
        "target_fps": _validate_int_range(1, 240),
        "quality": _validate_enum(("balanced", "high")),
    },
    "physics": {
        "timestep_hz": _validate_int_range(1, 2000),
        "substeps": _validate_int_range(1, 64),
        "gravity_m_s2": _validate_gravity,
        "reset_on_edit": _validate_bool,
    },
    "devices": {
        "discovery_enabled": _validate_bool,
        "telemetry_hz": _validate_int_range(1, 240),
        "actuation_enabled": _validate_literal_false,
    },
    "workspace": {
        "asset_search_paths": _validate_str_list,
        "reconstruction_status": _validate_nonempty_str,
    },
}


def validate_profile(profile: Any) -> dict:
    """Validate a complete settings profile.

    Returns ``{"valid": True, "errors": []}`` when valid, otherwise
    ``{"valid": False, "errors": [...]}`` with unique sorted section.field
    paths (or bare section/top-level names) and no field values.
    """
    if not isinstance(profile, dict):
        return {"valid": False, "errors": ["profile"]}

    errors: set = set()

    for section, fields in FIELDS.items():
        if section not in profile:
            errors.add(section)
            continue
        section_value = profile[section]
        if not isinstance(section_value, dict):
            errors.add(section)
            continue
        for field, validator in fields.items():
            if field not in section_value:
                errors.add(f"{section}.{field}")
            elif not validator(section_value[field]):
                errors.add(f"{section}.{field}")
        for extra_field in section_value:
            if extra_field not in fields:
                errors.add(f"{section}.{extra_field}")

    for extra_section in profile:
        if extra_section not in FIELDS:
            errors.add(extra_section)

    sorted_errors = sorted(errors)
    return {"valid": len(sorted_errors) == 0, "errors": sorted_errors}


def user_config_dir(app_name: str = "LeRTX") -> str:
    """Return the platform user configuration directory for this application."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, app_name)
    if os.uname().sysname == "Darwin":  # pragma: no cover - exercised on macOS hosts
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", app_name)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, app_name.lower())


def _without_credential(profile: dict) -> dict:
    """Return a deep copy of ``profile`` with the session-only API key removed."""
    redacted = copy.deepcopy(profile)
    if isinstance(redacted.get("llm"), dict):
        redacted["llm"]["api_key"] = ""
    return redacted


def save_profile(profile: dict, config_path: str) -> None:
    """Atomically persist a validated profile, never including the API key."""
    result = validate_profile(profile)
    if not result["valid"]:
        raise ValueError("cannot persist an invalid profile: " + ", ".join(result["errors"]))
    persisted = _without_credential(profile)
    directory = os.path.dirname(config_path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".lertx-config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(persisted, handle, sort_keys=True)
        os.replace(tmp_path, config_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def load_profile(config_path: str) -> dict:
    """Load a persisted profile, falling back to defaults when absent or invalid."""
    if not os.path.exists(config_path):
        return copy.deepcopy(DEFAULT_PROFILE)
    with open(config_path, "r", encoding="utf-8") as handle:
        try:
            loaded = json.load(handle)
        except ValueError:
            return copy.deepcopy(DEFAULT_PROFILE)
    if not validate_profile(loaded)["valid"]:
        return copy.deepcopy(DEFAULT_PROFILE)
    return loaded
