"""Subprocess protocol checks, including native-style and shutdown logging."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


class CliTests(unittest.TestCase):
    def test_native_subprocess_uses_explicit_declared_environment(self):
        from tests.test_launch_native import LaunchNativeTests
        result = subprocess.CompletedProcess([], 0,
            stdout=json.dumps({"application": "LeRTX", "closed": True}), stderr="")
        with patch("tests.test_launch_native.subprocess.run", return_value=result) as run:
            LaunchNativeTests()._check_cli_launch()
        self.assertEqual(run.call_args.kwargs["env"], dict(os.environ))
        self.assertIsNot(run.call_args.kwargs["env"], os.environ)
        self.assertEqual(run.call_args.kwargs["timeout"], 150)

    def test_result_isolated_from_python_fd_and_exit_logs(self):
        script = '''
import atexit, os
import main
def noisy_main(*arguments):
    print("python diagnostic", flush=True)
    os.write(1, b"native diagnostic\\n")
    atexit.register(lambda: os.write(1, b"shutdown diagnostic\\n"))
    return {"closed": True}
main.main = noisy_main
main._process_cli(['[{"command":"launch"}]'])
'''
        result = subprocess.run([sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"closed": True})
        for message in ("python diagnostic", "native diagnostic", "shutdown diagnostic"):
            self.assertIn(message, result.stderr)

    def test_normal_defaults_and_framework_modes_preserve_json(self):
        for argument in ('[{"command":"defaults"}]', '--litai-test', '--litai-smoke'):
            with self.subTest(argument=argument):
                result = subprocess.run([sys.executable, "main.py", argument],
                    cwd=Path(__file__).resolve().parents[1], capture_output=True,
                    text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsInstance(json.loads(result.stdout), dict)
