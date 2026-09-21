"""Exercise the exact offline installer and independent payload observer.

This disposable dependency check never imports application/SDK modules and is
not a lifecycle receipt or permission to execute generated application code.
"""

import argparse
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path

from literate_ai.adapters.builders.python import discover_python_toolchain
from literate_ai.adapters.dependencies.python_install import install_python_wheels
from literate_ai.adapters.dependencies.python_lock import (
    SCHEMA,
    parse_python_wheel_lock,
)
from literate_ai.adapters.dependencies.python_target import observe_python_wheel_target
from native_wheels import PINS, ROOTS, inspect


def run(directory: Path, command: str, installer: Path, temporary_root: Path) -> dict:
    archives = inspect(directory)
    if archives["status"] != "pass":
        raise ValueError("Archive verification failed")
    toolchain = discover_python_toolchain(pinned_command=command)
    target = observe_python_wheel_target(toolchain)
    fields = (
        "name",
        "version",
        "filename",
        "sha256",
        "requires_python",
        "requires_dist",
    )
    lock = parse_python_wheel_lock(
        json.dumps(
            {
                "schema": SCHEMA,
                "environment": dict(target.environment),
                "tags": list(target.tags),
                "requirements": [f"{name}=={PINS[name]}" for name in ROOTS],
                "packages": sorted(
                    (
                        {key: package[key] for key in fields}
                        for package in archives["packages"]
                    ),
                    key=lambda package: package["name"],
                ),
            }
        )
    )
    with ExitStack() as stack:
        sources = {
            package.name: stack.enter_context((directory / package.filename).open("rb"))
            for package in lock.packages
        }
        installer_stream = stack.enter_context(installer.open("rb"))
        with install_python_wheels(
            toolchain,
            lock,
            sources,
            installer_source=installer_stream,
            temporary_root=temporary_root,
        ) as installed:
            installed.revalidate()
            installed_path = installed.directory
            staged_path = installed.staged.directory
            report = {
                "schema": "lertx/native-wheel-install-review@1",
                "scope": "disposable-offline-install-not-application-admission",
                "target_identity": target.identity.uri,
                "installer_identity": installed.installer_identity.uri,
                "install_process_identity": installed.install_process_identity.uri,
                "installed_tree_identity": installed.observation.tree_identity.uri,
                "installed_files": len(installed.observation.files),
                "components": list(installed.observation.graph.components),
                "edges": [list(edge) for edge in installed.observation.graph.edges],
                "packages": archives["packages"],
                "revalidation": "pass",
                "verifier_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            }
    if installed_path.exists() or staged_path.exists():
        raise ValueError("Disposable installation cleanup failed")
    report.update(status="pass", cleanup="pass")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_directory", type=Path)
    parser.add_argument("--python", required=True)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--temporary-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    result = run(args.wheel_directory, args.python, args.installer, args.temporary_root)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {key: result[key] for key in ("status", "installed_files", "cleanup")}
        )
    )
