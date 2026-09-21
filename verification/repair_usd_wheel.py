"""Reproducibly repair only the reviewed USD 25.11 Linux wheel's metadata.

No extraction, installation, imports from the wheel, or validator changes.
The output directory must not exist. ZIP_STORED avoids compressor-version drift.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from literate_ai.adapters.dependencies.python_lock import (
    LockedPythonWheel,
    verify_locked_wheel,
)

FILENAME = "usd_core-25.11-cp311-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
ORIGINAL_SHA256 = "a971c76ee4470a318df0517109fa8302f4bfa4f42c1f26b011658bb2ae6b6fa4"
WHEEL = "usd_core-25.11.dist-info/WHEEL"
RECORD = "usd_core-25.11.dist-info/RECORD"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_hash(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(
        hashlib.sha256(data).digest()
    ).decode().rstrip("=")


def repair(source: Path, output: Path) -> dict:
    if source.is_symlink() or source.name != FILENAME:
        raise ValueError("Expected the exact regular-file USD wheel")
    original = source.read_bytes()
    if sha(original) != ORIGINAL_SHA256:
        raise ValueError("Original archive hash differs from reviewed input")
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive members")
        payload = {name: archive.read(name) for name in names}
        rows = list(csv.reader(io.StringIO(payload[RECORD].decode())))
        files = {i.filename for i in infos if not i.is_dir()}
        if len(rows) != len(files) or {r[0] for r in rows} != files:
            raise ValueError("Original RECORD inventory mismatch")
        for name, digest, size in rows:
            if name == RECORD:
                if digest or size:
                    raise ValueError("Unexpected RECORD self-hash")
            elif digest != record_hash(payload[name]) or size != str(
                len(payload[name])
            ):
                raise ValueError("Original payload RECORD mismatch: " + name)

        old_wheel = payload[WHEEL]
        lines = old_wheel.splitlines(keepends=True)
        fields = [line for line in lines if line.startswith(b"Root-Is-Purelib:")]
        if fields != [b"Root-Is-Purelib: true\n", b"Root-Is-Purelib: False\n"]:
            raise ValueError("Unexpected metadata defect")
        new_wheel = old_wheel.replace(
            fields[0], b"Root-Is-Purelib: false\n", 1
        ).replace(fields[1], b"", 1)
        old_row = f"{WHEEL},{record_hash(old_wheel)},{len(old_wheel)}".encode()
        new_row = f"{WHEEL},{record_hash(new_wheel)},{len(new_wheel)}".encode()
        if payload[RECORD].count(old_row) != 1:
            raise ValueError("Cannot uniquely replace WHEEL record")
        repaired = dict(payload)
        repaired[WHEEL] = new_wheel
        repaired[RECORD] = payload[RECORD].replace(old_row, new_row, 1)

        output.mkdir(parents=True, exist_ok=False)
        (output / "original").mkdir()
        (output / "repaired").mkdir()
        original_path = output / "original" / FILENAME
        with original_path.open("xb") as stream:
            stream.write(original)
        target = output / "repaired" / FILENAME
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_STORED) as result:
            result.comment = archive.comment
            for info in infos:
                member = copy.copy(info)
                member.compress_type = zipfile.ZIP_STORED
                result.writestr(member, repaired[info.filename])

    with zipfile.ZipFile(target) as result:
        if result.namelist() != names:
            raise ValueError("Repaired inventory changed")
        changes = [name for name in names if result.read(name) != payload[name]]
        if set(changes) != {WHEEL, RECORD}:
            raise ValueError("Non-metadata payload changed")
        for name in names:
            if result.read(name) != repaired[name]:
                raise ValueError("Written payload mismatch")
    with target.open("rb") as stream:
        repaired_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        package = LockedPythonWheel(
            "usd-core", "25.11", FILENAME, repaired_hash, ">=3.8, <3.14", ()
        )
        verified = verify_locked_wheel(package, stream)
    report = {
        "schema": "lertx/usd-wheel-metadata-repair@1",
        "status": "pass",
        "scope": "local-metadata-repair-not-installation-or-application-admission",
        "filename": FILENAME,
        "original_sha256": sha(original),
        "repaired_sha256": repaired_hash,
        "repair_script_sha256": sha(Path(__file__).read_bytes()),
        "zip_encoding": "ZIP_STORED; original member order and metadata retained",
        "root_is_purelib": "false",
        "changed_members": changes,
        "unchanged_members": [
            {"path": n, "sha256": sha(payload[n])} for n in names if n not in changes
        ],
        "strict_validator": "pass",
        "verified_members": len(verified),
    }
    with (output / "report.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = repair(args.source, args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "original_sha256",
                    "repaired_sha256",
                    "verified_members",
                )
            }
        )
    )
