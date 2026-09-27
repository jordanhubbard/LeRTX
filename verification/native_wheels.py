"""Check provisioned native wheels without extracting or executing their code.

Run with the reviewed parent framework on PYTHONPATH. This verifier records
archive consistency, not trusted acquisition, target compatibility, installation,
or permission to execute an application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.utils import canonicalize_name

from literate_ai.adapters.dependencies.python_lock import (
    SCHEMA,
    LockedPythonWheel,
    parse_python_wheel_lock,
    verify_locked_wheel,
)
from literate_ai.adapters.dependencies.types import DependencyObservationError

PINS = {
    "ovrtx": "0.5.0.377615",
    "ovstage": "0.2.0.377349",
    "newton": "1.6.0",
    "warp-lang": "1.17.0",
    "numpy": "2.4.6",
    "usd-core": "25.11",
    "pyside6": "6.10.2",
    "pyside6-addons": "6.10.2",
    "pyside6-essentials": "6.10.2",
    "shiboken6": "6.10.2",
    "pyserial": "3.5",
    "lertx-robot-assets": "1.0.0",
}
ROOTS = ("newton", "numpy", "ovrtx", "ovstage", "pyside6", "usd-core", "warp-lang", "pyserial", "lertx-robot-assets")


def inventory(packages):
    """Permit exactly one platform's declared USD provider, never both."""
    expected = dict(PINS)
    roots = ROOTS
    if any(package["name"] == "usd-exchange" for package in packages):
        del expected["usd-core"]
        expected["usd-exchange"] = "3.0.0"
        roots = tuple("usd-exchange" if name == "usd-core" else name for name in ROOTS)
    if {p["name"]: p["version"] for p in packages} != expected or len(packages) != len(expected):
        raise ValueError("Native application wheel inventory differs from the declared closure")
    return expected, tuple(sorted(roots))


def compatibility(archives: dict, target: dict) -> dict:
    """Check the Flavor's declared closure against captured target observations."""
    if archives.get("status") != "pass":
        raise ValueError("Compatibility requires successful archive verification")
    if target.get("schema") != "lertx/native-python-target-review@1":
        raise ValueError("Target input is not a native interpreter observation")
    packages = archives["packages"]
    pins, roots = inventory(packages)
    environment = target["environment"]
    arm_linux = environment["sys_platform"] == "linux" and environment["platform_machine"].lower() in ("arm64", "aarch64")
    if ("usd-exchange" in pins) != arm_linux:
        raise ValueError("USD provider differs from the target platform policy")
    fields = (
        "name",
        "version",
        "filename",
        "sha256",
        "requires_python",
        "requires_dist",
    )
    requirements = [f"{name}=={pins[name]}" for name in roots]
    lock = parse_python_wheel_lock(
        json.dumps(
            {
                "schema": SCHEMA,
                "environment": target["environment"],
                "tags": target["tags"],
                "requirements": requirements,
                "packages": sorted(
                    ({key: p[key] for key in fields} for p in packages),
                    key=lambda p: p["name"],
                ),
            }
        )
    )
    lock.require_target(target["environment"], target["tags"])
    return {
        "status": "pass",
        "scope": "compatibility-with-captured-target-not-installation-or-admission",
        "target_identity": target["target_identity"],
        "requirements": requirements,
        "edges": [list(edge) for edge in lock.edges],
    }


def inspect(directory: Path) -> dict:
    results = []
    seen = set()
    for path in sorted(directory.glob("*.whl")):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Wheel input must be a regular file")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            with zipfile.ZipFile(stream) as archive:
                entries = [
                    item
                    for item in archive.infolist()
                    if item.filename.endswith(".dist-info/METADATA")
                ]
                if len(entries) != 1 or entries[0].file_size > 4 * 1024 * 1024:
                    raise ValueError("Wheel metadata is ambiguous or oversized")
                metadata = BytesParser().parsebytes(archive.read(entries[0]))
            name = canonicalize_name(metadata["Name"])
            allowed = {**PINS, "usd-exchange": "3.0.0"}
            if name in seen or allowed.get(name) != metadata["Version"]:
                raise ValueError("Wheel inventory differs from native application pins")
            seen.add(name)
            package = LockedPythonWheel(
                name,
                metadata["Version"],
                path.name,
                digest,
                metadata.get("Requires-Python", ""),
                tuple(sorted(set(metadata.get_all("Requires-Dist", [])))),
            )
            result = {
                "name": name,
                "version": package.version,
                "filename": path.name,
                "sha256": digest,
                "bytes": path.stat().st_size,
                "requires_python": package.requires_python,
                "requires_dist": list(package.requires_dist),
            }
            try:
                payload = verify_locked_wheel(package, stream)
                result.update(
                    status="pass",
                    members=len(payload),
                    expanded_bytes=sum(p.size for p in payload),
                )
            except DependencyObservationError as exc:
                result.update(status="fail", error=str(exc))
            results.append(result)
    inventory(results)
    return {
        "schema": "lertx/native-wheel-archive-review@1",
        "scope": "archive-integrity-only-not-execution-admission",
        "status": "pass" if all(r["status"] == "pass" for r in results) else "fail",
        "packages": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    report = inspect(args.wheel_directory)
    if args.target is not None:
        target_bytes = args.target.read_bytes()
        report["compatibility"] = compatibility(report, json.loads(target_bytes))
        report["compatibility"]["target_report_sha256"] = hashlib.sha256(
            target_bytes
        ).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "packages": len(report["packages"])}))
    sys.exit(0 if report["status"] == "pass" else 1)
