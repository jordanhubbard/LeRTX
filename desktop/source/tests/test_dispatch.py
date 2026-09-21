import unittest

from lertx.app import main


class DispatchTests(unittest.TestCase):
    def test_non_object_payload_rejected(self):
        with self.assertRaises(ValueError):
            main("defaults")

    def test_missing_command_rejected(self):
        with self.assertRaises(ValueError):
            main({})

    def test_non_string_command_rejected(self):
        with self.assertRaises(ValueError):
            main({"command": 5})

    def test_unknown_command_rejected(self):
        with self.assertRaises(ValueError):
            main({"command": "reticulate-splines"})

    def test_unknown_field_on_defaults_rejected(self):
        with self.assertRaises(ValueError):
            main({"command": "defaults", "extra": 1})

    def test_validate_settings_requires_profile_field(self):
        with self.assertRaises(ValueError):
            main({"command": "validate-settings"})

    def test_unknown_field_on_validate_settings_rejected(self):
        with self.assertRaises(ValueError):
            main({"command": "validate-settings", "profile": {}, "extra": 1})


if __name__ == "__main__":
    unittest.main()
