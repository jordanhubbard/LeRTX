"""Startup regression checks; no SDK, GPU or network required."""
import importlib.util
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("desktop_manage", ROOT / "desktop/manage.py")
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = Path(self.directory.name)
        self.python = self.env / "python.exe"
        self.python.touch()
        for name, value in (("PYTHON", self.python), ("ENVIRONMENT", self.env),
                            ("SETUP_RECEIPT", self.env / "setup.json")):
            mock = patch.object(manage, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def mark_current(self):
        manage.SETUP_RECEIPT.write_text(json.dumps(manage.setup_identity()), encoding="utf-8")

    def test_missing_or_corrupt_receipt_requires_setup(self):
        self.assertFalse(manage.setup_is_current())
        manage.SETUP_RECEIPT.write_text("incomplete", encoding="utf-8")
        self.assertFalse(manage.setup_is_current())

    def test_current_receipt_needs_existing_interpreter(self):
        self.mark_current()
        self.assertTrue(manage.setup_is_current())
        self.python.unlink()
        self.assertFalse(manage.setup_is_current())

    def test_changed_inputs_require_setup(self):
        self.mark_current()
        changed = dict(manage.setup_identity(), inputs="changed-lock")
        with patch.object(manage, "setup_identity", return_value=changed):
            self.assertFalse(manage.setup_is_current())

    def test_receipt_only_written_after_warmup(self):
        with patch.object(manage, "run"), patch.object(manage, "warmup") as warmup:
            manage.setup()
            warmup.assert_called_once()
        self.assertTrue(manage.setup_is_current())

    def test_failed_refresh_invalidates_previous_success(self):
        self.mark_current()
        with patch.object(manage, "run"), patch.object(manage, "warmup", side_effect=RuntimeError("GPU failed")):
            with self.assertRaisesRegex(RuntimeError, "GPU failed"):
                manage.setup()
        self.assertFalse(manage.setup_is_current())

    def test_first_install_can_finish_after_five_minutes(self):
        # Model a slow but successful shader compile without making CI sleep.
        with patch.object(manage.subprocess, "Popen") as popen:
            process = popen.return_value.__enter__.return_value
            def completed(timeout):
                if timeout < 600:
                    raise subprocess.TimeoutExpired("shader preparation", timeout)
                return 0
            process.wait.side_effect = completed
            manage.warmup()
            process.kill.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Windows process-tree cleanup")
    def test_warmup_timeout_kills_windows_children_and_fails_setup(self):
        self.mark_current()
        with patch.object(manage, "run"), \
                patch.object(manage.subprocess, "Popen") as popen, \
                patch.object(manage.subprocess, "run") as taskkill:
            process = popen.return_value.__enter__.return_value
            process.pid = 12345
            process.wait.side_effect = [subprocess.TimeoutExpired("warmup", 900), 1]
            with self.assertRaises(subprocess.TimeoutExpired):
                manage.setup()
            self.assertEqual(taskkill.call_args.args[0],
                             ["taskkill", "/PID", "12345", "/T", "/F"])
            process.kill.assert_called_once()
        self.assertFalse(manage.setup_is_current())

    def test_first_run_builds_before_launch_and_forwards_scene(self):
        events = []
        with patch.object(sys, "argv", ["manage.py", "run", "--scene", "scene with spaces.usda"]), \
             patch.object(manage, "setup", side_effect=lambda: events.append("setup")), \
             patch.object(manage, "run", side_effect=lambda *a, **kw: events.append(a)):
            manage.main()
        self.assertEqual(events[0], "setup")
        payload = json.loads(events[1][0][-1])[0]
        self.assertEqual(payload["command"], "launch")
        self.assertTrue(payload["scene"].endswith("scene with spaces.usda"))

    def test_current_run_skips_setup(self):
        self.mark_current()
        with patch.object(sys, "argv", ["manage.py", "run"]), \
             patch.object(manage, "setup") as setup, patch.object(manage, "run") as launch:
            manage.main()
        setup.assert_not_called()
        launch.assert_called_once()

    def test_setup_failure_prevents_launch(self):
        with patch.object(sys, "argv", ["manage.py", "run"]), \
             patch.object(manage, "setup", side_effect=RuntimeError("install failed")), \
             patch.object(manage, "run") as launch:
            with self.assertRaisesRegex(RuntimeError, "install failed"):
                manage.main()
        launch.assert_not_called()

    def test_build_checks_receipt_and_reuses_successful_setup(self):
        with patch.object(sys, "argv", ["manage.py", "build"]), \
                patch.object(manage, "setup") as setup:
            manage.main()
            setup.assert_called_once()
            setup.reset_mock()
            self.mark_current()
            manage.main()
            setup.assert_not_called()

    def test_install_checks_setup_before_creating_launcher(self):
        events = []
        with patch.object(sys, "argv", ["manage.py", "install"]), \
                patch.object(manage, "setup", side_effect=lambda: events.append("setup")), \
                patch.object(manage, "install_launcher", side_effect=lambda: events.append("install")):
            manage.main()
        self.assertEqual(events, ["setup", "install"])

    def test_install_reuses_only_an_unchanged_owned_launcher(self):
        destination = self.env / "LeRTX.lnk"
        destination.write_bytes(b"existing launcher")
        receipt = self.env / "lertx-launcher.json"
        receipt.write_text(json.dumps({"path": str(destination),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
        with patch.object(manage, "launcher_path", return_value=destination), patch.object(manage, "run") as run:
            manage.install_launcher()
            run.assert_not_called()
            destination.write_bytes(b"user edited launcher")
            with self.assertRaisesRegex(RuntimeError, "Launcher already exists"):
                manage.install_launcher()
            receipt.unlink()
            with self.assertRaises(RuntimeError):manage.install_launcher()

    def test_robot_models_retain_their_pinned_upstream_bytes(self):
        resources = ROOT / "desktop/source/lertx/resources/so101"
        provenance = json.loads((resources / "provenance.json").read_text())
        for path in resources.glob("*.urdf"):
            with self.subTest(model=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                                 provenance["files"]["Simulation/SO101/" + path.name])

    def test_authoring_files_keep_canonical_lf_newlines(self):
        paths = list((ROOT / "components").rglob("*.md"))
        paths.extend((ROOT / "skills").rglob("SKILL.md"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(b"\r\n" not in path.read_bytes(), "Noncanonical CRLF checkout")

    def test_vendor_sdk_retains_checksum_pinned_bytes(self):
        vendor = ROOT / "desktop/source/lertx/vendor/feetech"
        provenance = json.loads((vendor / "provenance.json").read_text())
        for name, expected in provenance["files"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((vendor / name).read_bytes()).hexdigest(), expected)

    @unittest.skipUnless(sys.platform == "win32", "Windows entry point")
    def test_powershell_wrapper_forwards_paths_and_exit_code(self):
        root = self.env / "checkout with spaces"
        (root / "desktop").mkdir(parents=True)
        (root / "run.ps1").write_bytes((ROOT / "run.ps1").read_bytes())
        (root / "desktop/manage.py").write_text(
            "import json,sys; print(json.dumps(sys.argv[1:])); sys.exit(7)", encoding="utf-8")
        result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 "-File", str(root / "run.ps1"), "-Scene", "scene with spaces.usda"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["run", "--scene", "scene with spaces.usda"])

    def test_darwin_lock_omits_ovrtx_and_pins_metal(self):
        lock = ROOT / "desktop/locks/darwin-arm64.txt"
        self.assertTrue(lock.is_file(), "darwin-arm64 hash lock must exist")
        text = lock.read_text()
        self.assertNotIn("ovrtx", text)
        self.assertNotIn("ovstage", text)
        self.assertIn("usd-core==26.8", text)
        self.assertIn("newton==1.7.0", text)
        self.assertIn("warp-lang==1.18.0", text)
        self.assertIn("pyside6==6.12.0", text)
        self.assertIn("pyobjc-framework-metal", text.lower())

    def test_darwin_launcher_is_an_executable_command_script(self):
        destination = Path(self.directory.name) / "Applications" / "LeRTX.command"
        with patch.object(manage.sys, "platform", "darwin"), \
                patch.object(manage, "os", SimpleNamespace(name="posix")), \
                patch.object(manage, "launcher_path", return_value=destination):
            manage.install_launcher()
        text = destination.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/bash"))
        self.assertIn(" run", text)
        self.assertTrue(os.access(destination, os.X_OK))

    def test_make_run_routes_launch_and_propagates_failure(self):
        make = shutil.which("make") or shutil.which("gmake")
        self.assertIsNotNone(make, "GNU Make is required for the startup CI gate")
        root = self.env / "make checkout with spaces"
        (root / "desktop").mkdir(parents=True)
        for name in ("Makefile", "run.ps1"):
            (root / name).write_bytes((ROOT / name).read_bytes())
        marker = root / "invocation.json"
        (root / "desktop/manage.py").write_text(
            "import json,pathlib,sys; "
            "pathlib.Path('invocation.json').write_text(json.dumps(sys.argv[1:])); "
            "sys.exit(7)", encoding="utf-8")
        result = subprocess.run([make, "run", f'PYTHON="{sys.executable}"'],
                                cwd=root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((root / ".venv").exists())
        self.assertEqual(json.loads(marker.read_text()), ["run"])
        self.assertIn("7", result.stderr)

    def test_make_build_and_install_route_without_unix_utilities(self):
        make = shutil.which("make") or shutil.which("gmake")
        self.assertIsNotNone(make)
        root = self.env / "build checkout with spaces"
        (root / "desktop").mkdir(parents=True)
        (root / "Makefile").write_bytes((ROOT / "Makefile").read_bytes())
        (root / "desktop/manage.py").write_text(
            "import os,pathlib,sys; "
            "f=pathlib.Path('commands.txt').open('a'); f.write(sys.argv[1]+'\\n'); f.close(); "
            "sys.exit(int(os.environ.get('LERTX_TEST_EXIT','0')))", encoding="utf-8")
        marker = root / "commands.txt"
        for target, expected in (("build", ["build"]), ("install", ["build", "install"])):
            with self.subTest(target=target):
                marker.unlink(missing_ok=True)
                result = subprocess.run([make, target, f'PYTHON="{sys.executable}"'], cwd=root,
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(marker.read_text().splitlines(), expected)
        marker.unlink()
        result = subprocess.run([make, "install", f'PYTHON="{sys.executable}"'], cwd=root,
            env={**os.environ, "LERTX_TEST_EXIT": "7"}, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        self.assertEqual(marker.read_text().splitlines(), ["build"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
