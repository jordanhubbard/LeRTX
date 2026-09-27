"""Platform policy must agree with the native wheel closure, without SDK imports."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lertx import host


class HostTests(unittest.TestCase):
    def test_supported_target_matrix_and_usd_provider(self):
        for system, machine, provider in (
            ("linux", "x86_64", "usd-core"),
            ("linux", "aarch64", "usd-exchange"),
            ("linux", "arm64", "usd-exchange"),
            ("win32", "AMD64", "usd-core"),
        ):
            for minor in (11, 12):
                with self.subTest(system=system, machine=machine, minor=minor), \
                        patch.object(host.sys, "platform", system), \
                        patch.object(host.sys, "version_info", SimpleNamespace(major=3, minor=minor)), \
                        patch.object(host.platform, "machine", return_value=machine):
                    host.check_native_support()
                    self.assertEqual(host.usd_distribution(), provider)

    def test_unsupported_targets_fail_before_native_initialization(self):
        for system, machine, minor in (
            ("win32", "ARM64", 11), ("darwin", "arm64", 11),
            ("linux", "i686", 11), ("linux", "aarch64", 14),
        ):
            with self.subTest(system=system, machine=machine, minor=minor), \
                    patch.object(host.sys, "platform", system), \
                    patch.object(host.sys, "version_info", SimpleNamespace(major=3, minor=minor)), \
                    patch.object(host.platform, "machine", return_value=machine):
                with self.assertRaises(host.UnsupportedHostError):
                    host.check_native_support()
