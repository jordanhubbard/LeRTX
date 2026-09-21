"""Generated implementation-test cases (native behavior evidence).

This module independently recalculates every expectation encoded in the
disposable ``source/tests/manifest.json`` lifecycle manifest. It never
reads, embeds, or parses that manifest file; it is executable evidence,
not a reflection of it.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Tuple

from lertx.config import DEFAULT_PROFILE

REFS = ("component.md",)


@dataclass(frozen=True)
class Case:
    case_id: str
    category: str
    specification_refs: Tuple[str, ...]
    arguments: Tuple[Any, ...]
    expected_result: Any


def _profile(overrides: dict) -> dict:
    profile = copy.deepcopy(DEFAULT_PROFILE)
    for path, value in overrides.items():
        section, field = path.split(".")
        profile[section][field] = value
    return profile


def _profile_with_extra_section() -> dict:
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["extra"] = {}
    return profile


def _profile_without_section(name: str) -> dict:
    profile = copy.deepcopy(DEFAULT_PROFILE)
    del profile[name]
    return profile


def _profile_with_extra_field(section: str, field: str, value: Any) -> dict:
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile[section][field] = value
    return profile


def _invalid(*errors: str) -> dict:
    return {"valid": False, "errors": sorted(errors)}


_VALID = {"valid": True, "errors": []}

CASES = [
    Case(
        "defaults-basic",
        "example",
        REFS,
        ({"command": "defaults"},),
        copy.deepcopy(DEFAULT_PROFILE),
    ),
    Case(
        "validate-default-profile-valid",
        "example",
        REFS,
        ({"command": "validate-settings", "profile": copy.deepcopy(DEFAULT_PROFILE)},),
        _VALID,
    ),
    Case(
        "max-output-tokens-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.max_output_tokens": 131072})},),
        _VALID,
    ),
    Case(
        "max-output-tokens-above-upper-bound",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.max_output_tokens": 131073})},),
        _invalid("llm.max_output_tokens"),
    ),
    Case(
        "max-output-tokens-zero-invalid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.max_output_tokens": 0})},),
        _invalid("llm.max_output_tokens"),
    ),
    Case(
        "timeout-seconds-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.timeout_seconds": 300})},),
        _VALID,
    ),
    Case(
        "timeout-seconds-above-upper-bound",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.timeout_seconds": 301})},),
        _invalid("llm.timeout_seconds"),
    ),
    Case(
        "substeps-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.substeps": 64})},),
        _VALID,
    ),
    Case(
        "substeps-above-upper-bound",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.substeps": 65})},),
        _invalid("physics.substeps"),
    ),
    Case(
        "substeps-zero-invalid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.substeps": 0})},),
        _invalid("physics.substeps"),
    ),
    Case(
        "timestep-hz-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.timestep_hz": 2000})},),
        _VALID,
    ),
    Case(
        "timestep-hz-above-upper-bound",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.timestep_hz": 2001})},),
        _invalid("physics.timestep_hz"),
    ),
    Case(
        "telemetry-hz-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"devices.telemetry_hz": 240})},),
        _VALID,
    ),
    Case(
        "telemetry-hz-above-upper-bound",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"devices.telemetry_hz": 241})},),
        _invalid("devices.telemetry_hz"),
    ),
    Case(
        "target-fps-upper-bound-valid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"rendering.target_fps": 240})},),
        _VALID,
    ),
    Case(
        "target-fps-zero-invalid",
        "boundary",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"rendering.target_fps": 0})},),
        _invalid("rendering.target_fps"),
    ),
    Case(
        "unknown-top-level-section",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile_with_extra_section()},),
        _invalid("extra"),
    ),
    Case(
        "missing-section",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile_without_section("workspace")},),
        _invalid("workspace"),
    ),
    Case(
        "multiple-invalid-fields-sorted",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile({"general.theme": "blue", "rendering.quality": "ultra"}),
            },
        ),
        _invalid("general.theme", "rendering.quality"),
    ),
    Case(
        "device-negative-invalid",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"rendering.device": -1})},),
        _invalid("rendering.device"),
    ),
    Case(
        "remember-key-true-invalid",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"llm.remember_key": True})},),
        _invalid("llm.remember_key"),
    ),
    Case(
        "actuation-enabled-true-invalid",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"devices.actuation_enabled": True})},),
        _invalid("devices.actuation_enabled"),
    ),
    Case(
        "profile-null-invalid",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": None},),
        _invalid("profile"),
    ),
    Case(
        "endpoint-userinfo-invalid",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile(
                    {"llm.endpoint": "https://user:pass@inference-api.nvidia.com/v1/responses"}
                ),
            },
        ),
        _invalid("llm.endpoint"),
    ),
    Case(
        "endpoint-non-https-invalid",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile({"llm.endpoint": "http://inference-api.nvidia.com/v1/responses"}),
            },
        ),
        _invalid("llm.endpoint"),
    ),
    Case(
        "endpoint-fragment-invalid",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile(
                    {"llm.endpoint": "https://inference-api.nvidia.com/v1/responses#frag"}
                ),
            },
        ),
        _invalid("llm.endpoint"),
    ),
    Case(
        "endpoint-credential-query-invalid",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile(
                    {"llm.endpoint": "https://inference-api.nvidia.com/v1/responses?api_key=abc"}
                ),
            },
        ),
        _invalid("llm.endpoint"),
    ),
    Case(
        "gravity-non-numeric-invalid",
        "invariant",
        REFS,
        ({"command": "validate-settings", "profile": _profile({"physics.gravity_m_s2": "abc"})},),
        _invalid("physics.gravity_m_s2"),
    ),
    Case(
        "asset-search-paths-non-string-invalid",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile({"workspace.asset_search_paths": [1, 2]}),
            },
        ),
        _invalid("workspace.asset_search_paths"),
    ),
    Case(
        "unknown-field-inside-section",
        "invariant",
        REFS,
        (
            {
                "command": "validate-settings",
                "profile": _profile_with_extra_field("general", "foo", "bar"),
            },
        ),
        _invalid("general.foo"),
    ),
]

SMOKE_CASE = CASES[0]

assert len({case.case_id for case in CASES}) == len(CASES)
assert 3 <= len(CASES) <= 256
