"""Native behavior tests matching every case in ``manifest_cases``.

These are the executable evidence backing ``source/tests/manifest.json``;
they call the real application logic directly and never parse that file.
"""
import unittest

from lertx.app import main
from tests.manifest_cases import CASES


def _make_test(case):
    def _test(self):
        self.assertEqual(main(*case.arguments), case.expected_result)

    return _test


class ManifestCaseTests(unittest.TestCase):
    pass


for _case in CASES:
    setattr(ManifestCaseTests, f"test_{_case.case_id.replace('-', '_')}", _make_test(_case))


if __name__ == "__main__":
    unittest.main()
