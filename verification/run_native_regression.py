"""Exercise the mixed Qt/native regression suite in desktop startup order.

Qt must own the display connection before OVRTX initializes EGL. Creating Qt only
after earlier headless SDK sessions crashed libEGL_nvidia on the Omarchy worker.
Run through native_guard.py with the worker's native display environment.
"""
from pathlib import Path
import argparse
import sys
import unittest

source=Path(__file__).resolve().parents[1]/'desktop/source'
sys.path[:0]=[str(source),str(source/'tests')]
from lertx.ui import build_application


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', help='Run one test module in a fresh SDK process')
    args=parser.parse_args()
    application=build_application([])
    suite=unittest.defaultTestLoader.loadTestsFromNames([args.module] if args.module else [
        'test_runtime_native','test_robot_render_native','test_window_native',
        'test_runtime_idle','test_runtime_settings','test_mock_ui'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    application.quit()
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
