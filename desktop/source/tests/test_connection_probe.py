import threading
import time
import unittest
from lertx.transport import ConnectionProbe


class ConnectionProbeTests(unittest.TestCase):
    def test_bounded_request_and_stale_result(self):
        release = threading.Event()
        def tester(*args, cancel_token):
            release.wait(2)
            return {"state": "success"}
        probe = ConnectionProbe(tester)
        first = probe.start(())
        try:
            self.assertIsNotNone(first)
            self.assertIsNone(probe.start(()))
            probe.cancel(first)
            self.assertEqual(probe.poll(first), {"state": "cancelled"})
            self.assertIsNone(probe.start(()))
        finally:
            release.set()
        deadline = time.monotonic()+2
        while not probe._future.done() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(probe._future.done())
        self.assertEqual(probe.poll(first), {"state": "cancelled"})
