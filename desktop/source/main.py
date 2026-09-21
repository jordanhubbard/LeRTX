"""LeRTX desktop application entrypoint.

Normal invocation: one command-line argument containing a complete UTF-8
JSON array of positional arguments for :func:`main`, e.g. ``'[{"command":
"defaults"}]'``. Two framework-owned, non-product modes run before that
parsing: ``--litai-test`` and ``--litai-smoke``.
"""
from __future__ import annotations

import json
import os
import sys

from lertx.app import main


def _run_litai_test(output) -> None:
    from tests import manifest_cases

    cases_outcomes = []
    any_failed = False
    for case in manifest_cases.CASES:
        try:
            actual = main(*case.arguments)
            passed = actual == case.expected_result
        except Exception:  # noqa: BLE001 - a raising case is a failing case
            passed = False
        if not passed:
            any_failed = True
        cases_outcomes.append({"case_id": case.case_id, "outcome": "passed" if passed else "failed"})

    output.write(
        json.dumps({"schema": "literate-ai/generated-test-results@1", "cases": cases_outcomes})
    )
    output.write("\n")
    if any_failed:
        sys.exit(1)


def _run_litai_smoke(output) -> None:
    from tests import manifest_cases

    case = manifest_cases.SMOKE_CASE
    result = main(*case.arguments)
    output.write(json.dumps(result))
    output.write("\n")


def _run_cli(argv: list, output=None) -> None:
    output = sys.stdout if output is None else output
    if argv == ["--litai-test"]:
        _run_litai_test(output)
        return
    if argv == ["--litai-smoke"]:
        _run_litai_smoke(output)
        return
    if len(argv) != 1:
        raise SystemExit("expected exactly one JSON array argument")
    arguments = json.loads(argv[0])
    if not isinstance(arguments, list):
        raise SystemExit("the single command-line argument must be a JSON array")
    result = main(*arguments)
    output.write(json.dumps(result))
    output.write("\n")


def _process_cli(argv: list) -> None:
    """Reserve stdout for the protocol, including during native shutdown.

    Process entry only: redirection deliberately lasts through interpreter exit,
    because native destructors can log after the final result has been written.
    Library callers of app.main do not have their process descriptors changed.
    """
    sys.stdout.flush()
    result_fd = os.dup(sys.stdout.fileno())
    try:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        if os.name == "nt":
            # Native DLLs may use the Win32 handle instead of Python's CRT fd.
            import ctypes
            from ctypes import wintypes
            import msvcrt
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.SetStdHandle.argtypes = (wintypes.DWORD, wintypes.HANDLE)
            kernel.SetStdHandle.restype = wintypes.BOOL
            if not kernel.SetStdHandle(0xfffffff5, msvcrt.get_osfhandle(sys.stderr.fileno())):
                raise ctypes.WinError(ctypes.get_last_error())
        with os.fdopen(result_fd, "w", encoding="utf-8", closefd=False) as output:
            _run_cli(argv, output)
    finally:
        os.close(result_fd)


if __name__ == "__main__":
    _process_cli(sys.argv[1:])
