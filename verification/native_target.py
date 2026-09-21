"""Observe one native worker interpreter without importing its SDK packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from literate_ai.adapters.builders.python import discover_python_toolchain
from literate_ai.adapters.dependencies.python_target import observe_python_wheel_target


def observe(command: str) -> dict:
    toolchain = discover_python_toolchain(pinned_command=command)
    target = observe_python_wheel_target(toolchain)
    return {
        "schema": "lertx/native-python-target-review@1",
        "scope": "interpreter-compatibility-only-not-installation-or-admission",
        "target_identity": target.identity.uri,
        "probe_identity": target.probe_identity.uri,
        "environment": dict(target.environment),
        "tags": list(target.tags),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error("output already exists")
    report = observe(arguments.python)
    with arguments.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"target_identity": report["target_identity"]}))
