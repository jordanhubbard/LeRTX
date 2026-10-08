import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lertx.config import DEFAULT_PROFILE, load_profile, save_profile
from lertx.runtime import SceneWorker


class RuntimeSettingsTests(unittest.TestCase):
    def test_color_change_rebuilds_runtime_and_rejects_live_hardware(self):
        candidate=copy.deepcopy(self.previous);candidate['general']['leader_color']='#123456'
        self.worker._hardware_roles.add('leader')
        with self.assertRaisesRegex(ValueError,'Close hardware'):
            self.worker.configure(candidate,self.path)
        self.worker._hardware_roles.clear()
        with patch.object(self.worker,'rebuild',return_value={}) as rebuild:
            self.worker.configure(candidate,self.path)
        rebuild.assert_called_once()
        self.assertEqual(load_profile(self.path)['general']['leader_color'],'#123456')
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name)/"settings.json")
        self.previous = copy.deepcopy(DEFAULT_PROFILE)
        save_profile(self.previous, self.path)
        self.before = Path(self.path).read_bytes()
        self.worker = SceneWorker(copy.deepcopy(self.previous))
        self.worker.document = object()
        self.candidate = copy.deepcopy(self.previous)
        self.candidate["rendering"]["width"] = 640
        self.candidate["llm"]["api_key"] = "must-never-be-written"

    def test_persistence_follows_successful_native_application(self):
        def rebuild():
            self.assertEqual(Path(self.path).read_bytes(), self.before)
            self.assertEqual(self.worker.profile["rendering"]["width"], 640)
            return {"native":"ready"}
        with patch.object(self.worker, "rebuild", side_effect=rebuild):
            self.assertEqual(self.worker.configure(self.candidate, self.path), {"native":"ready"})
        self.assertEqual(load_profile(self.path)["rendering"]["width"], 640)
        self.assertNotIn(b"must-never-be-written", Path(self.path).read_bytes())

    def test_failed_native_rebuild_restores_prior_profile_without_persisting(self):
        with patch.object(self.worker, "rebuild", side_effect=[ValueError("private failure"), {}]) as rebuild:
            with self.assertRaisesRegex(ValueError, "previous configuration restored") as error:
                self.worker.configure(self.candidate, self.path)
            self.assertEqual(rebuild.call_count, 2)
        self.assertNotIn("private failure", str(error.exception))
        self.assertEqual(self.worker.profile, self.previous)
        self.assertEqual(Path(self.path).read_bytes(), self.before)

    def test_persistence_failure_rolls_native_profile_back(self):
        profiles = []
        def rebuild():
            profiles.append(copy.deepcopy(self.worker.profile))
            return {}
        with patch.object(self.worker, "rebuild", side_effect=rebuild), \
                patch("lertx.config.save_profile", side_effect=OSError("disk failure")):
            with self.assertRaises(ValueError):
                self.worker.configure(self.candidate, self.path)
        self.assertEqual(profiles, [self.candidate, self.previous])
        self.assertEqual(self.worker.profile, self.previous)
        self.assertEqual(Path(self.path).read_bytes(), self.before)

    def test_failed_restoration_is_fatal_and_does_not_claim_ready(self):
        with patch.object(self.worker, "rebuild", side_effect=OSError("native failure")):
            with self.assertRaisesRegex(RuntimeError, "native restoration failed"):
                self.worker.configure(self.candidate, self.path)
        self.assertEqual(Path(self.path).read_bytes(), self.before)

    def test_non_native_settings_do_not_rebuild_or_reset_simulation(self):
        candidate = copy.deepcopy(self.previous)
        candidate["llm"]["model"] = "changed-model"
        self.worker.clock.play()
        self.worker.clock.sim_time = 12
        with patch.object(self.worker, "status", return_value={}), patch.object(self.worker, "rebuild") as rebuild:
            self.worker.configure(candidate, self.path)
        rebuild.assert_not_called()
        self.assertTrue(self.worker.clock.playing)
        self.assertEqual(self.worker.clock.sim_time, 12)

    def test_invalid_profile_is_rejected_before_changes(self):
        self.candidate["rendering"]["width"] = 0
        with self.assertRaisesRegex(ValueError, "Invalid application settings"):
            self.worker.configure(self.candidate, self.path)
        self.assertEqual(self.worker.profile, self.previous)
        self.assertEqual(Path(self.path).read_bytes(), self.before)
