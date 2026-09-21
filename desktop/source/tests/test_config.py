import copy
import os
import tempfile
import unittest

from lertx import config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(config.validate_profile(config.DEFAULT_PROFILE), {"valid": True, "errors": []})

    def test_endpoint_rejects_malformed_hosts_ports_and_encoded_credentials(self):
        for endpoint in ("https://[broken", "https://example.com:bad", "https://example.com:65536",
                         "https://example.com:0", "https://:443", "https://exa mple.com",
                         "https://example.com/\npath", "https://example.com/?%61pi_key=secret",
                         "https://example.com/?to%6ben=secret"):
            with self.subTest(endpoint=endpoint):
                profile = copy.deepcopy(config.DEFAULT_PROFILE)
                profile["llm"]["endpoint"] = endpoint
                self.assertEqual(config.validate_profile(profile),
                                 {"valid": False, "errors": ["llm.endpoint"]})

    def test_endpoint_accepts_ipv6_and_noncredential_query(self):
        profile = copy.deepcopy(config.DEFAULT_PROFILE)
        profile["llm"]["endpoint"] = "https://[::1]:8443/v1/responses?api-version=2026-01-01"
        self.assertEqual(config.validate_profile(profile), {"valid": True, "errors": []})

    def test_non_object_profile_is_invalid(self):
        self.assertEqual(config.validate_profile("not-a-profile"), {"valid": False, "errors": ["profile"]})

    def test_missing_field_reported(self):
        profile = copy.deepcopy(config.DEFAULT_PROFILE)
        del profile["llm"]["model"]
        self.assertEqual(config.validate_profile(profile), {"valid": False, "errors": ["llm.model"]})

    def test_gravity_accepts_positive_finite_decimal(self):
        profile = copy.deepcopy(config.DEFAULT_PROFILE)
        profile["physics"]["gravity_m_s2"] = "9.81"
        self.assertEqual(config.validate_profile(profile), {"valid": True, "errors": []})

    def test_save_profile_redacts_api_key(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile = copy.deepcopy(config.DEFAULT_PROFILE)
            profile["llm"]["api_key"] = "super-secret"
            config_path = os.path.join(tmp_dir, "settings.json")
            config.save_profile(profile, config_path)
            with open(config_path, "r", encoding="utf-8") as handle:
                raw = handle.read()
            self.assertNotIn("super-secret", raw)

    def test_save_profile_rejects_invalid_profile(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile = copy.deepcopy(config.DEFAULT_PROFILE)
            profile["general"]["theme"] = "not-a-theme"
            config_path = os.path.join(tmp_dir, "settings.json")
            with self.assertRaises(ValueError):
                config.save_profile(profile, config_path)
            self.assertFalse(os.path.exists(config_path))

    def test_load_profile_falls_back_to_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "missing.json")
            self.assertEqual(config.load_profile(config_path), config.DEFAULT_PROFILE)

    def test_load_profile_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile = copy.deepcopy(config.DEFAULT_PROFILE)
            profile["general"]["theme"] = "light"
            config_path = os.path.join(tmp_dir, "settings.json")
            config.save_profile(profile, config_path)
            loaded = config.load_profile(config_path)
            self.assertEqual(loaded["general"]["theme"], "light")


if __name__ == "__main__":
    unittest.main()
