"""Startup regression checks; no SDK, GPU or network required."""
import importlib.util
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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
        if sys.platform == "darwin":
            self.assertIn("LeRTX cannot render on macOS", result.stderr)
            self.assertFalse(marker.exists(), "Unsupported Mac must not start setup")
        else:
            self.assertEqual(json.loads(marker.read_text()), ["run"])
            self.assertIn("7", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
