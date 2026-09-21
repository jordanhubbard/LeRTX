"""Integration checks using the exact locally provisioned original wheel."""

import os
import tempfile
import unittest
from pathlib import Path

from repair_usd_wheel import FILENAME, repair


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["LERTX_ORIGINAL_USD_WHEEL"])

    def test_reproducible_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = repair(self.source, root / "a")
            second = repair(self.source, root / "b")
            self.assertEqual(first, second)
            self.assertEqual(
                (root / "a/repaired" / FILENAME).read_bytes(),
                (root / "b/repaired" / FILENAME).read_bytes(),
            )
            with self.assertRaises(FileExistsError):
                repair(self.source, root / "a")

    def test_modified_input_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / FILENAME
            source.write_bytes(self.source.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                repair(source, root / "output")
            self.assertFalse((root / "output").exists())

    def test_symlink_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / FILENAME
            source.symlink_to(self.source)
            with self.assertRaisesRegex(ValueError, "regular-file"):
                repair(source, root / "output")
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
