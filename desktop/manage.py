"""Install and operate the retained desktop in an isolated project environment."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "desktop" / "source"
ENVIRONMENT = ROOT / ".venv"
PYTHON = ENVIRONMENT / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SETUP_RECEIPT = ENVIRONMENT / "lertx-setup.json"


def setup_identity():
    """Invalidate cached setup when the checkout or pinned inputs change."""
    inputs = [Path(__file__).resolve(), SOURCE / "requirements.txt"]
    inputs.extend(sorted((ROOT / "desktop/locks").glob("*.txt")))
    inputs.extend(sorted((ROOT / "desktop/wheels").glob("*.whl")))
    digest = hashlib.sha256()
    for path in inputs:
        digest.update(str(path.relative_to(ROOT)).encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return {"schema": 1, "root": str(ROOT), "platform": sys.platform,
            "machine": platform.machine(), "inputs": digest.hexdigest()}


def setup_is_current():
    if not PYTHON.is_file():
        return False
    try:
        return json.loads(SETUP_RECEIPT.read_text(encoding="utf-8")) == setup_identity()
    except (OSError, ValueError):
        return False


def run(arguments, **kwargs):
    return subprocess.run([str(value) for value in arguments], check=True, **kwargs)


def setup():
    # A failed refresh must never leave an earlier successful receipt in use.
    SETUP_RECEIPT.unlink(missing_ok=True)
    identity = setup_identity()
    if not PYTHON.exists():
        uv = shutil.which("uv")
        if uv:
            run([uv, "venv", "--python", "3.11", "--seed", ENVIRONMENT])
        elif sys.version_info[:2] in ((3, 11), (3, 12)):
            run([sys.executable, "-m", "venv", ENVIRONMENT])
        elif shutil.which("python3.11"):
            run(["python3.11", "-m", "venv", ENVIRONMENT])
        elif shutil.which("py") and os.name == "nt":
            run(["py", "-3.11", "-m", "venv", ENVIRONMENT])
        else:
            raise RuntimeError("Install Python 3.11 or uv, then run this setup command again.")
    # Fail before downloading large wheels on an unsupported host/interpreter.
    run([PYTHON, "-c", "from lertx.host import check_native_support; check_native_support()"], cwd=SOURCE)
    run([PYTHON, "-m", "ensurepip"])
    machine = platform.machine().lower()
    target = "linux-arm64" if sys.platform == "linux" and machine in ("aarch64", "arm64") else (
        "windows-x86_64" if os.name == "nt" else "linux-x86_64")
    lock = ROOT / "desktop" / "locks" / f"{target}.txt"
    run([PYTHON, "-m", "pip", "install", "--only-binary=:all:",
         "--require-hashes", "--find-links", ROOT / "desktop/wheels", "--extra-index-url", "https://pypi.nvidia.com",
         "-r", lock])
    run([PYTHON, "-m", "pip", "check"])
    run([PYTHON, "-B", "-c", "from lertx.diagnostics import main; main()"], cwd=SOURCE)
    warmup()
    temporary = SETUP_RECEIPT.with_suffix(".tmp")
    temporary.write_text(json.dumps(identity), encoding="utf-8")
    temporary.replace(SETUP_RECEIPT)


def warmup():
    command = [str(PYTHON), "-B", "-m", "lertx.warmup"]
    with subprocess.Popen(command, cwd=SOURCE) as process:
        try:
            result = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                # Windows venv Python delegates to another process. Killing only
                # the launcher would leave its native GPU worker running.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               check=False, capture_output=True, timeout=15)
            process.kill()
            process.wait(timeout=15)
            raise
        if result:
            raise subprocess.CalledProcessError(result, command)


def launcher_path():
    if os.name == "nt":
        return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/LeRTX.lnk"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "applications/lertx.desktop"


def install_launcher():
    destination = launcher_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Launcher already exists: {destination}. Remove it with uninstall before reinstalling.")
    if os.name == "nt":
        # PowerShell single-quoted literals escape apostrophes by doubling them.
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        script = (
            "$ErrorActionPreference='Stop'; $shell=New-Object -ComObject WScript.Shell; "
            f"$link=$shell.CreateShortcut({quote(destination)}); "
            f"$link.TargetPath={quote(PYTHON.with_name('pythonw.exe'))}; "
            f"$link.Arguments={quote(chr(34) + str(Path(__file__).resolve()) + chr(34) + ' run')}; "
            f"$link.WorkingDirectory={quote(ROOT)}; $link.Description='LeRTX digital-twin workspace'; $link.Save()"
        )
        run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    else:
        def quote(value):
            value = str(value)
            if any(c in value for c in "\n\r"):
                raise RuntimeError("Desktop launcher paths cannot contain newlines.")
            # Desktop Entry Exec has its own escaping rules, not shell syntax.
            value = value.replace("\\", "\\\\\\\\").replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
            return '"' + value + '"'
        destination.write_text(
            "[Desktop Entry]\nType=Application\nName=LeRTX\n"
            "Comment=Robot digital-twin workspace\n"
            f"Exec={quote(PYTHON)} {quote(Path(__file__).resolve())} run\n"
            "Terminal=false\nCategories=Graphics;Science;\nStartupWMClass=LeRTX\n",
            encoding="utf-8",
        )
    (ENVIRONMENT / "lertx-launcher.json").write_text(json.dumps({
        "path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()
    }), encoding="utf-8")
    print(f"Installed launcher: {destination}")


def uninstall_launcher():
    receipt = ENVIRONMENT / "lertx-launcher.json"
    if not receipt.is_file():
        raise RuntimeError("No launcher installed by this checkout; nothing was removed.")
    identity = json.loads(receipt.read_text(encoding="utf-8"))
    path = Path(identity["path"])
    if path != launcher_path():
        raise RuntimeError("Launcher location changed; nothing was removed.")
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != identity["sha256"]:
        raise RuntimeError("Launcher was modified; nothing was removed.")
    path.unlink(missing_ok=True)
    receipt.unlink()
    print("Removed LeRTX launcher. Project environment and user documents are preserved.")


def package():
    destination = ROOT / "dist" / "LeRTX-prototype.zip"
    destination.parent.mkdir(exist_ok=True)
    files = [ROOT / "desktop" / "manage.py", ROOT / "desktop" / "README.md"]
    files.append(ROOT / "run.ps1")
    files.append(ROOT / 'docs/user/hardware.md')
    files.extend(SOURCE / name for name in ("main.py", "desktop_main.py", "requirements.txt", "pytest.ini", "tests/manifest.json"))
    files.extend(p for p in (SOURCE/'lertx').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    for name in ("tests", "tools"):
        files.extend((SOURCE / name).glob("*.py"))
    files.extend((ROOT / "desktop/locks").glob("*.txt"))
    files.extend((ROOT / "desktop/wheels").glob("*.whl"))
    files.extend((ROOT / "verification/acceptance/scenes").glob("*.usda"))
    # The small source bundle needs no compressor. Storing entries also avoids
    # platform zlib differences, so Windows and Linux produce identical bytes.
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_STORED) as archive:
        for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix()):
            info = zipfile.ZipInfo("LeRTX/" + path.relative_to(ROOT).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "doctor", "run", "test", "warmup", "install", "uninstall", "package"))
    parser.add_argument("--scene", type=Path, help="USD file to open with run")
    args = parser.parse_args()
    if args.scene and args.command != "run":
        parser.error("--scene is only valid with run")
    if args.command == "package":
        package()
        return
    if args.command == "uninstall":
        uninstall_launcher()
        return
    if args.command == "setup":
        setup()
        print("LeRTX environment ready. Run: python desktop/manage.py run")
        return
    if args.command == "run" and not setup_is_current():
        print("Preparing LeRTX for this checkout...", flush=True)
        setup()
    if not PYTHON.exists():
        raise RuntimeError("LeRTX is not installed. Run: python desktop/manage.py setup")
    if args.command == "install":
        install_launcher()
        return
    if args.command == "warmup":
        warmup()
        return
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if args.command == "doctor":
        run([PYTHON, "-c", "from lertx.diagnostics import main; main()"],
            cwd=SOURCE, env=environment)
    elif args.command == "test":
        run([PYTHON, "tools/run_tests.py"], cwd=SOURCE, env=environment)
    else:
        payload = {"command": "launch"}
        if args.scene:
            payload["scene"] = str(args.scene.resolve())
        command = [PYTHON, "main.py", json.dumps([payload])]
        if os.name == "nt" and sys.stdout is None:
            (ROOT / "_build").mkdir(exist_ok=True)
            with (ROOT / "_build/desktop.log").open("a", encoding="utf-8") as log:
                run(command, cwd=SOURCE, env=environment, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            run(command, cwd=SOURCE, env=environment)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"LeRTX: {error}", file=sys.stderr)
        sys.exit(1)
