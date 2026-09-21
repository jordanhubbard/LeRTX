"""LeRTX desktop application entrypoint.

Normal invocation: one command-line argument containing a complete UTF-8
JSON array of positional arguments for :func:`main`, e.g. ``'[{"command":
"defaults"}]'``. Two framework-owned, non-product modes run before that
parsing: ``--litai-test`` and ``--litai-smoke``.
"""
from __future__ import annotations

import json
import sys

from lertx.app import main


def _run_litai_test() -> None:
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

    sys.stdout.write(
        json.dumps({"schema": "literate-ai/generated-test-results@1", "cases": cases_outcomes})
    )
    sys.stdout.write("\n")
    if any_failed:
        sys.exit(1)


def _run_litai_smoke() -> None:
    from tests import manifest_cases

    case = manifest_cases.SMOKE_CASE
    result = main(*case.arguments)
    sys.stdout.write(json.dumps(result))
    sys.stdout.write("\n")


def _run_cli(argv: list) -> None:
    if argv == ["--litai-test"]:
        _run_litai_test()
        return
    if argv == ["--litai-smoke"]:
        _run_litai_smoke()
        return
    if len(argv) != 1:
        raise SystemExit("expected exactly one JSON array argument")
    arguments = json.loads(argv[0])
    if not isinstance(arguments, list):
        raise SystemExit("the single command-line argument must be a JSON array")
    result = main(*arguments)
    sys.stdout.write(json.dumps(result))
    sys.stdout.write("\n")


if __name__ == "__main__":
    _run_cli(sys.argv[1:])
