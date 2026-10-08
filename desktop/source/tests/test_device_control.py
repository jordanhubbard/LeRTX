"""Shared ownership exercised against the real serial worker and SDK emulator."""
import tempfile
import time
import unittest
from pathlib import Path

from lertx.device_control import DeviceRegistry
from lertx.devices import Candidate
from lertx.hardware import HardwareSession
from lertx.usb_bus import FeetechBus
from tests.test_setup import CalibrationSerial


class DeviceControlTests(unittest.TestCase):
    def setUp(self):
        self.serial = CalibrationSerial()
        self.created = []
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.candidate = Candidate('shared-device', 1, 2, 'serial')
        def factory(candidate, role):
            session = HardwareSession(candidate, role, verify=lambda c: None,
                bus_factory=lambda p: FeetechBus(p, serial_factory=lambda **k: self.serial))
            self.created.append(session)
            return session
        self.registry = DeviceRegistry(factory)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.registry.shutdown()
        for session in self.created:
            self.assertTrue(session.wait_closed(3))

    def wait(self, predicate, *accesses):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            for access in accesses:
                access.heartbeat()
            if predicate():
                return
            time.sleep(.01)
        self.fail('Device controller transition timed out')

    def connect(self):
        access = self.registry.acquire(self.candidate, 'follower')
        access.request('connect')
        self.wait(lambda: access.snapshot()['state'] == 'read-only', access)
        return access

    def test_setup_reuses_port_and_observer_close_does_not_stop_calibration(self):
        hardware = self.connect()
        setup = self.registry.acquire(self.candidate, 'follower', 'setup')
        self.assertIs(hardware.controller, setup.controller)
        self.assertEqual(len(self.created), 1)
        setup.request('connect')  # Idempotent: the existing connection remains open.
        with self.assertRaises(ValueError):
            hardware.request('arm')
        setup.request('setup_begin', Path(self.directory.name)/'backup.json')
        self.wait(lambda: (setup.snapshot()['setup'] or {}).get('state') == 'recording', setup)
        hardware.stop(shutdown=True, force=False)
        self.assertFalse(hardware.alive)
        self.assertTrue(setup.alive)
        self.assertEqual(setup.snapshot()['setup']['state'], 'recording')
        self.assertTrue(setup.writable)

    def test_cancel_restores_before_returning_control_to_existing_hardware(self):
        hardware = self.connect()
        setup = self.registry.acquire(self.candidate, 'follower', 'setup')
        setup.request('setup_begin', Path(self.directory.name)/'backup.json')
        self.wait(lambda: (setup.snapshot()['setup'] or {}).get('state') == 'recording', setup)
        setup.stop(shutdown=True, force=False)
        self.assertFalse(hardware.writable)
        self.wait(lambda: not setup.alive, setup)
        self.assertTrue(hardware.writable)
        self.assertEqual(hardware.snapshot()['setup']['state'], 'cancelled')
        self.assertTrue(hardware.alive)
        self.assertEqual(len(self.created), 1)

    def test_failed_restore_never_hands_writes_to_an_observer(self):
        hardware = self.connect()
        setup = self.registry.acquire(self.candidate, 'follower', 'setup')
        setup.request('setup_begin', Path(self.directory.name)/'backup.json')
        self.wait(lambda: (setup.snapshot()['setup'] or {}).get('state') == 'recording', setup)
        def failed_restore(*args):
            raise ConnectionError('injected restore failure')
        self.created[0].bus.write_calibration = failed_restore
        setup.stop(shutdown=True, force=False)
        self.wait(lambda: not setup.alive, setup)
        self.assertFalse(hardware.writable)
        self.assertFalse(hardware.alive)
        self.assertEqual(hardware.snapshot()['setup']['state'], 'restore-unconfirmed')
        with self.assertRaises(ValueError):
            hardware.request('arm')

    def test_roles_and_attachments_cannot_alias_live_controllers(self):
        self.connect()
        with self.assertRaises(ValueError):
            self.registry.acquire(self.candidate, 'leader')
        with self.assertRaises(ValueError):
            self.registry.acquire(Candidate('other', 1, 2, 'different'), 'follower')
        self.assertEqual(len(self.created), 1)

    def test_pending_engage_blocks_setup_before_worker_processes_it(self):
        hardware = self.connect()
        hardware.request('arm')
        with self.assertRaisesRegex(ValueError, 'release motors'):
            self.registry.acquire(self.candidate, 'follower', 'setup')

    def test_only_owner_heartbeat_and_commands_reach_worker(self):
        hardware = self.connect()
        setup = self.registry.acquire(self.candidate, 'follower', 'setup')
        from unittest.mock import patch
        with patch.object(self.created[0], 'heartbeat') as heartbeat:
            hardware.heartbeat(True)
            heartbeat.assert_not_called()
            setup.heartbeat(False)
            heartbeat.assert_called_once_with(False)
        with self.assertRaises(ValueError):
            setup.request('arm')

    def test_cancelled_connect_can_be_explicitly_retried(self):
        access = self.registry.acquire(self.candidate, 'follower')
        from unittest.mock import patch
        with patch.object(self.created[0], 'request'):
            access.request('connect')
        stop = access.stop(force=False)
        self.wait(lambda: access.snapshot()['stop_completed'] >= stop, access)
        access.heartbeat()
        access.request('connect')
        self.wait(lambda: access.snapshot()['state'] == 'read-only', access)

    def test_application_shutdown_closes_shared_session_once(self):
        hardware = self.connect()
        self.registry.acquire(self.candidate, 'follower', 'observer')
        self.registry.shutdown()
        self.wait(lambda: not self.registry.alive)
        self.assertFalse(hardware.alive)
        with self.assertRaises(ValueError):
            self.registry.acquire(self.candidate, 'follower')
