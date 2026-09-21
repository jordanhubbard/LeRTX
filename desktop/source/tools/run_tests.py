"""Discover and run every generated unittest module under ``source/tests``.

Uses only the standard library so no additional test-framework dependency
is introduced. Exits nonzero when any test fails or errors.
"""
from __future__ import annotations

import os
import sys
import unittest


def main() -> int:
    source_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(source_root, "tests"), top_level_dir=source_root)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
