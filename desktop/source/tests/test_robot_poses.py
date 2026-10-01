"""Portable (no Qt) tests for named joint-pose presets."""
import json
import tempfile
import unittest
from pathlib import Path

from lertx.robot import JOINT_NAMES
from lertx.robot_poses import BUILTIN_DIR, list_presets, load_pose, save_pose


class BundledPresetTests(unittest.TestCase):
    def test_bundled_presets_exist_and_are_valid(self):
        names = {path.stem for path in BUILTIN_DIR.glob('*.json')}
        self.assertIn('danger', names)
        self.assertIn('the_signal', names)
        for path in BUILTIN_DIR.glob('*.json'):
            fractions = load_pose(path)
            for role in ('leader', 'follower'):
                self.assertEqual(set(fractions[role]), set(JOINT_NAMES))
                for value in fractions[role].values():
                    self.assertGreaterEqual(value, 0.)
                    self.assertLessEqual(value, 1.)

    def test_bundled_presets_use_their_label_field(self):
        labels = {label for label, _path, builtin in list_presets('/tmp/unused-config.json') if builtin}
        self.assertIn('Danger', labels)
        self.assertIn('The Signal', labels)


class SaveLoadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = str(Path(self.directory.name) / 'settings.json')

    def test_round_trip_preserves_values(self):
        fractions = {'leader': {name: .25 for name in JOINT_NAMES},
                     'follower': {name: .75 for name in JOINT_NAMES}}
        path = save_pose(self.config_path, 'My Pose', fractions)
        self.assertEqual(path.name, 'My Pose.json')
        loaded = load_pose(path)
        self.assertEqual(loaded, fractions)
        labels = [(label, builtin) for label, _path, builtin in list_presets(self.config_path)]
        self.assertIn(('My Pose', False), labels)

    def test_rejects_empty_or_path_breaking_names(self):
        fractions = {'leader': {name: .5 for name in JOINT_NAMES}, 'follower': {name: .5 for name in JOINT_NAMES}}
        with self.assertRaises(ValueError):
            save_pose(self.config_path, '', fractions)
        with self.assertRaises(ValueError):
            save_pose(self.config_path, 'a/b', fractions)

    def test_rejects_out_of_range_or_missing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text(json.dumps({'schema': 1, 'leader': {name: 1.5 for name in JOINT_NAMES},
                                         'follower': {name: .5 for name in JOINT_NAMES}}))
            with self.assertRaises(ValueError):
                load_pose(path)
            path.write_text(json.dumps({'schema': 1, 'leader': {}, 'follower': {}}))
            with self.assertRaises(ValueError):
                load_pose(path)


if __name__ == '__main__':
    unittest.main()
