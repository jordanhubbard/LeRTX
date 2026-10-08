"""Check the scoped desktop release and construct its reproducible assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True, timeout=180,
                   env=dict(os.environ, QT_QPA_PLATFORM="offscreen",
                            PYTHONDONTWRITEBYTECODE="1"))


def check():
    evidence = json.loads((ROOT / "verification/sdk-refresh-review.json").read_text())
    source = ROOT / "desktop/source"
    expected = evidence["source_binding"]["files_relative_to_desktop_source"]
    actual = {p.relative_to(source).as_posix(): digest(p)
              for p in source.rglob("*") if p.is_file()
              and not {"__pycache__", ".pytest_cache"}.intersection(p.parts)
              and p.suffix not in (".pyc", ".pyo")}
    if actual != expected:
        raise RuntimeError("Application source differs from native qualification")
    native = evidence["linux_native"]
    if native["status"] != "passed" or native["tests"] != 17:
        raise RuntimeError("Missing native qualification")
    for result in native["native_modules"]:
        if result["returncode"] != 0 or result["guard"]["status"] != "passed":
            raise RuntimeError("Failed native module")
    # Every portable module runs in a fresh Qt process. GPU-only modules have
    # separately retained native evidence above; absence of a GPU is no pass.
    excluded = {"test_native_integration.py", "test_robot_dynamics.py"}
    modules = [p for p in sorted((source / "tests").glob("test_*.py"))
               if not p.name.endswith("_native.py") and p.name not in excluded]
    if not modules:
        raise RuntimeError("No portable tests discovered")
    for module in modules:
        run(sys.executable, "-m", "pytest", str(module), "-q")
    run(sys.executable, "-m", "pytest", "verification/test_robot_asset_wheel.py", "-q")
    package()


def package():
    run(sys.executable, "desktop/manage.py", "package")
    bundle = ROOT / "dist/LeRTX-prototype.zip"
    before = digest(bundle)
    run(sys.executable, "desktop/manage.py", "package")
    if digest(bundle) != before:
        raise RuntimeError("Source bundle is not reproducible")
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise RuntimeError("Invalid source bundle")
        for name in names:
            relative = Path(name).relative_to("LeRTX")
            if ".." in relative.parts or archive.read(name) != (ROOT / relative).read_bytes():
                raise RuntimeError("Package member differs from source")
    version = json.loads((ROOT / "literate.project.json").read_text())["version"]
    destination = ROOT / f"dist/LeRTX-{version}.zip"
    destination.write_bytes(bundle.read_bytes())
    checksum = destination.with_suffix(".zip.sha256")
    checksum.write_text(f"{before}  {destination.name}\n", encoding="utf-8")
    value = {
        "schema": "literate-ai/qualified-release-files@1",
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "version": version,
        "files": [{"role": role, "path": p.relative_to(ROOT).as_posix(),
                   "size": p.stat().st_size, "identity": "sha256:" + digest(p)}
                  for role, p in (("source-setup", destination), ("checksums", checksum))],
    }
    value["identity"] = "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    (ROOT / "dist/release-files.json").write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args()
    package() if args.package_only else check()
