"""Real application entrypoint, including its Qt event loop and temporary scene."""
from pathlib import Path
import tempfile
import time
import unittest
import json
import os
import subprocess
import sys
from unittest.mock import patch

from lertx import app, ui


class LaunchNativeTests(unittest.TestCase):
    def test_cli_launch_stdout_is_only_json_with_real_native_shutdown(self):
        self._check_cli_launch()

    def test_cli_existing_file_in_fresh_process_initializes_usd_before_rtx(self):
        from lertx.scene import create_default_scene
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"existing.usda"
            create_default_scene(str(path))
            self._check_cli_launch(str(path))

    def _check_cli_launch(self, scene=None):
        script = '''
import faulthandler, json, runpy, sys, tempfile, time
from unittest.mock import patch
from PySide6.QtCore import QTimer
from lertx import ui
from lertx.scene import NativeWorker
faulthandler.dump_traceback_later(60, repeat=True, file=sys.stderr)
original = ui.build_main_window
original_initialize = NativeWorker._initialize
initializations = []
def initialize(worker):
    initializations.append(True)
    return original_initialize(worker)
scene = sys.argv[1] if len(sys.argv) > 1 else None
frames = []
def factory(*args, **kwargs):
    window = original(*args, **kwargs)
    timer = QTimer(window)
    deadline = time.monotonic() + 90
    def finish():
        if window._image is not None or time.monotonic() > deadline:
            frames.append(window._image is not None)
            if window._image is None:
                print("First-frame timeout:", window.native_status_label.text(), file=sys.stderr)
                faulthandler.dump_traceback(file=sys.stderr)
            else:
                print("CLI test: first frame received; closing window", file=sys.stderr)
            timer.stop()
            window.close()
    timer.timeout.connect(finish)
    timer.start(30)
    return window
with tempfile.TemporaryDirectory() as directory, \\
        patch("lertx.config.user_config_dir", return_value=directory), \\
        patch("lertx.ui.build_main_window", side_effect=factory), \\
        patch.object(NativeWorker, "_initialize", initialize):
    payload = {"command":"launch"}
    if scene is not None:
        payload["scene"] = scene
    sys.argv = ["main.py", json.dumps([payload])]
    runpy.run_module("main", run_name="__main__")
faulthandler.cancel_dump_traceback_later()
if frames != [True]:
    raise SystemExit("No native frame reached the actual CLI window")
if initializations != [True]:
    raise SystemExit("CLI startup created an unused native renderer")
'''
        try:
            result = subprocess.run([sys.executable, "-c", script] + ([scene] if scene else []),
                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                # The Windows SDK mutates native PATH outside os.environ.
                # Launch from the declared Python environment, not that parent
                # process's native loader state, to test a fresh application.
                text=True, timeout=150, env=dict(os.environ))
        except subprocess.TimeoutExpired as exc:
            diagnostics = exc.stderr or ""
            if isinstance(diagnostics, bytes):
                diagnostics = diagnostics.decode("utf-8", errors="replace")
            self.fail("CLI exceeded the 150-second deadline:\n" + diagnostics[-16000:])
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        self.assertEqual(json.loads(result.stdout), {"application": "LeRTX", "closed": True})

    def test_launch_returns_only_after_native_close_and_removes_untitled(self):
        from PySide6.QtCore import QTimer
        original_factory = ui.build_main_window
        scenes, observations = [], []
        def factory(*args, **kwargs):
            window = original_factory(*args, **kwargs)
            scenes.append(Path(args[2]))
            deadline = time.monotonic()+90
            timer = QTimer(window)
            def close_when_ready():
                if window._image is not None:
                    observations.append((True, window.requires_save_as))
                    timer.stop()
                    window.close()
                elif time.monotonic() > deadline:
                    observations.append((False, window.native_status_label.text()))
                    timer.stop()
                    window.close()
            timer.timeout.connect(close_when_ready)
            timer.start(30)
            return window
        with tempfile.TemporaryDirectory() as directory, \
                patch("lertx.config.user_config_dir", return_value=directory), \
                patch("lertx.ui.build_main_window", side_effect=factory):
            for _ in range(2):
                self.assertEqual(app.main({"command": "launch"}),
                                 {"application": "LeRTX", "closed": True})
        self.assertEqual(observations, [(True, True), (True, True)])
        self.assertNotEqual(scenes[0], scenes[1])
        self.assertTrue(all(not scene.parent.exists() for scene in scenes))
