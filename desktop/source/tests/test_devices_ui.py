import copy
from pathlib import Path
import tempfile
import threading
import time
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.devices import Candidate, scan_candidates
from lertx.devices_ui import build_devices_dialog
from lertx.transport import ConnectionProbe
from lertx.ui import build_application


class DevicesUiTests(unittest.TestCase):
    def setUp(self):
        self.app = build_application([])
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"devices.json"
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.reject()
            dialog.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def dialog(self, tester):
        dialog = build_devices_dialog(copy.deepcopy(DEFAULT_PROFILE), ConnectionProbe(tester), self.path)
        self.dialogs.append(dialog)
        dialog.show()
        return dialog

    def wait(self, predicate):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        self.fail("Device panel condition timed out")

    def test_visible_assignment_disconnect_and_ambiguity(self):
        a = Candidate("A",1,2,"serial-A","Adapter A")
        candidates = [a]
        dialog = self.dialog(lambda **kwargs:{"state":"success","candidates":list(candidates)})
        self.wait(lambda: dialog.last_scan_ok)
        dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0))
        dialog.assign_buttons["leader"].click()
        self.assertIn("telemetry disconnected",dialog.role_labels["leader"].text())
        self.assertTrue(self.path.exists())
        candidates.clear()
        dialog.scan_button.click()
        self.wait(lambda: "No USB" in dialog.status.text())
        self.assertIn("missing",dialog.role_labels["leader"].text())
        candidates.extend([a,Candidate("B",1,2,"serial-A")])
        dialog.scan_button.click()
        self.wait(lambda: "ambiguous" in dialog.role_labels["leader"].text())

    def test_scan_failure_is_not_no_devices(self):
        dialog = self.dialog(lambda **kwargs:{"state":"scan_failed"})
        self.wait(lambda: "enumeration failed" in dialog.status.text())
        self.assertFalse(dialog.assign_buttons["leader"].isEnabled())

    def test_close_ignores_late_scan(self):
        release = threading.Event()
        def slow(**kwargs):
            release.wait(5)
            return {"state":"success","candidates":[Candidate("A",1,2)]}
        dialog = self.dialog(slow)
        try:
            dialog.reject()
            release.set()
            self.app.processEvents()
            self.assertFalse(dialog.active)
            self.assertEqual(dialog.candidates,[])
        finally:
            release.set()

    def test_native_metadata_enumeration_has_no_duplicate_ports(self):
        # Real OS enumeration, no expectation that hardware is attached.
        candidates = scan_candidates()
        self.assertEqual(len({c.port for c in candidates}),len(candidates))
        self.assertTrue(all(0 <= c.vendor <= 65535 and 0 <= c.product <= 65535 for c in candidates))
