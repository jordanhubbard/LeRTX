"""Portable regressions for the parent wheel-observer Windows repair draft."""

from contextlib import contextmanager
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from literate_ai.adapters.dependencies.types import DependencyObservationError
from tests.unit.test_python_installed import PythonInstalledTests


class WindowsWheelMetadataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PythonInstalledTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.install_fixture()

    def test_enumeration_metadata_does_not_supply_custody_identity(self):
        real_scandir = os.scandir

        @contextmanager
        def incomplete_scandir(directory):
            with real_scandir(directory) as entries:
                rows = []
                for entry in entries:
                    observed = Path(entry.path).lstat()
                    incomplete = SimpleNamespace(
                        st_mode=observed.st_mode,
                        st_file_attributes=getattr(observed, "st_file_attributes", 0),
                        st_dev=0,
                        st_ino=0,
                        st_nlink=0,
                    )
                    rows.append(
                        SimpleNamespace(
                            path=entry.path,
                            stat=lambda *, follow_symlinks=False, value=incomplete: (
                                value
                            ),
                        )
                    )
                yield iter(rows)

        with self.fixture.stage() as staged:
            with patch("os.scandir", incomplete_scandir):
                result = self.fixture.observe(staged)
            self.assertTrue(result.files)

    def test_full_metadata_still_rejects_hardlinked_payload(self):
        payload = self.fixture.installed / "example/__init__.py"
        os.link(payload, self.fixture.root / "external-hardlink.py")
        with (
            self.fixture.stage() as staged,
            self.assertRaisesRegex(DependencyObservationError, "link or special"),
        ):
            self.fixture.observe(staged)


if __name__ == "__main__":
    unittest.main(defaultTest="WindowsWheelMetadataTests")
