import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lertx.devices import Candidate, RoleAssignments


class DeviceRolesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"devices.json"
        self.roles = RoleAssignments(self.path)
        self.a = Candidate("port-A", 1, 2, "serial-A")
        self.b = Candidate("port-B", 1, 2, "serial-B")

    def tearDown(self):
        self.directory.cleanup()

    def test_persistent_identity_survives_port_rename_and_reorder(self):
        self.assertEqual(self.roles.assign("leader", self.a, [self.a,self.b]), "persistent")
        self.roles.assign("follower", self.b, [self.a,self.b])
        loaded = RoleAssignments(self.path)
        renamed = Candidate("new-port",1,2,"serial-A")
        self.assertEqual(loaded.resolve("leader", [self.b,renamed]), ("assigned",renamed))
        self.assertNotIn("port-A", self.path.read_text())
        self.assertNotIn("serial-A", self.path.read_text())

    def test_missing_device_never_substitutes_another(self):
        self.roles.assign("leader",self.a,[self.a])
        self.assertEqual(self.roles.resolve("leader", [self.b]), ("missing",None))

    def test_duplicate_identity_is_ambiguous_and_cannot_occupy_other_role(self):
        self.roles.assign("leader",self.a,[self.a])
        duplicate = Candidate("port-C",1,2,"serial-A")
        self.assertEqual(self.roles.resolve("leader", [self.a,duplicate]), ("ambiguous",None))
        with self.assertRaises(ValueError):
            self.roles.assign("follower",duplicate,[self.a,duplicate])

    def test_missing_and_duplicate_serials_use_session_only(self):
        for serial in ("", "duplicated"):
            a, b = Candidate("A",1,2,serial), Candidate("B",1,2,serial)
            self.assertEqual(self.roles.assign("leader",a,[a,b]), "session-only")
            self.assertEqual(self.roles.resolve("leader",[a,b]), ("assigned",a))
            self.assertEqual(RoleAssignments(self.path).resolve("leader",[a,b]), ("unassigned",None))
            self.roles.update([b])
            self.roles.update([a,b])
            self.assertEqual(self.roles.resolve("leader",[a,b]), ("unassigned",None))

    def test_one_port_cannot_take_both_roles(self):
        self.roles.assign("leader",self.a,[self.a,self.b])
        with self.assertRaises(ValueError):
            self.roles.assign("follower",self.a,[self.a,self.b])

    def test_failed_persistence_preserves_assignments_and_file(self):
        self.roles.assign("leader",self.a,[self.a,self.b])
        before = self.path.read_bytes()
        with patch("lertx.devices.os.replace", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                self.roles.assign("leader",self.b,[self.a,self.b])
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.roles.resolve("leader",[self.a,self.b]), ("assigned",self.a))
        self.assertEqual(list(self.path.parent.glob(".lertx-devices-*")), [])

    def test_invalid_config_preserved(self):
        for raw in ('{"schema":true,"roles":{}}', '{"schema":1,"schema":1,"roles":{}}', '['*2000+']'*2000):
            self.path.write_text(raw)
            with self.assertRaisesRegex(ValueError,"file preserved"):
                RoleAssignments(self.path)
            self.assertEqual(self.path.read_text(),raw)
