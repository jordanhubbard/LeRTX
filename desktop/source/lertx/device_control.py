"""Application-owned device sessions and scoped control access.

Registry/controller methods run on the UI thread. HardwareSession alone owns the
serial worker. Readers share snapshots; only the active access supplies commands
and heartbeats. No Qt dependencies or window references belong in this module.
"""
from .hardware import HardwareSession
from .usb_bus import port_key


class DeviceRegistry:
    def __init__(self, session_factory=HardwareSession):
        self.session_factory = session_factory
        self._controllers = {}
        self.closing = False

    def acquire(self, candidate, role, purpose="hardware", session_factory=None):
        if self.closing:
            raise ValueError("Application device services are closing")
        key = port_key(candidate.port)
        for controller in self.active_controllers():
            same_port = port_key(controller.candidate.port) == key
            if same_port and (controller.role != role or
                    controller.candidate.attachment[1:] != candidate.attachment[1:]):
                raise ValueError("This USB attachment already belongs to " + controller.role)
            if controller.role == role and not same_port:
                raise ValueError("Close the existing " + role + " device before changing its USB attachment")
        controller = self._controllers.get(key)
        if controller is None or not controller.session.alive:
            factory = session_factory or self.session_factory
            controller = DeviceController(factory(candidate, role))
            self._controllers[key] = controller
        return controller.acquire(purpose)

    def active_controllers(self):
        return [c for c in self._controllers.values() if c.session.alive]

    @property
    def alive(self):
        return bool(self.active_controllers())

    def wait_closed(self, timeout=5):
        import time
        deadline = time.monotonic() + timeout
        return all(c.session.wait_closed(max(0, deadline-time.monotonic()))
                   for c in self._controllers.values())

    def shutdown(self):
        self.closing = True
        for controller in self.active_controllers():
            controller.session.stop(shutdown=True, force=False)


class DeviceController:
    def __init__(self, session):
        self.session = session
        self.candidate = session.candidate
        self.role = session.role
        self.calibration = None
        self.binding = None
        self._accesses = []
        self._writer = None
        self._engage_stop_sequence = None
        self._connecting = False
        self._connect_stop_sequence = 0

    def acquire(self, purpose):
        if purpose not in ("hardware", "setup", "session", "observer"):
            raise ValueError("Unknown device access purpose")
        snapshot = self.session.snapshot()
        self._reconcile(snapshot)
        if any(a.closing for a in self._accesses):
            raise ValueError("Wait for device stop and calibration recovery to complete")
        if purpose in ("setup","session"):
            if self._writer and self._writer.purpose in ("setup","session"):
                raise ValueError("This arm already has an active "+self._writer.purpose+" controller")
            sample = snapshot["sample"]
            if (self._engage_stop_sequence is not None or
                    snapshot["state"] in ("armed", "arming") or
                    (sample and any(m["torque"] for m in sample["motors"].values()))):
                raise ValueError("Support the arm and release motors in hardware controls before changing device control")
        access = DeviceAccess(self, purpose)
        self._accesses.append(access)
        if purpose in ("setup","session") or (self._writer is None and purpose != "observer"):
            self._writer = access
            self.session.heartbeat(False)
        return access

    def _reconcile(self, snapshot):
        if (self._engage_stop_sequence is not None and
                snapshot["stop_completed"] > self._engage_stop_sequence):
            self._engage_stop_sequence = None
        if (snapshot["state"] != "disconnected" or not snapshot["alive"] or
                snapshot["stop_completed"] > self._connect_stop_sequence):
            self._connecting = False
        for access in list(self._accesses):
            if access.closing and (not snapshot["alive"] or
                    (access._stop_sequence is not None and
                     snapshot["stop_completed"] >= access._stop_sequence)):
                # A failed recovery must never enable another writer.
                failed = snapshot["stop_confirmed"] is False or (
                    snapshot.get("setup") or {}).get("state") == "restore-unconfirmed"
                if failed and snapshot["alive"]:
                    access._stop_sequence = None
                    self.session.stop(shutdown=True, force=False)
                    continue
                self._detach(access)

    def _detach(self, access):
        if access in self._accesses:
            self._accesses.remove(access)
        access.closed = True
        if self._writer is access:
            self._writer = next((a for a in self._accesses
                                 if not a.closing and a.purpose == "hardware"), None)

    def release(self, access, completed=False):
        if access.closed or access.closing:
            return
        if completed and access.purpose == "setup":
            snapshot = self.session.snapshot()
            if (snapshot.get("setup") or {}).get("state") != "saved":
                raise ValueError("Setup must be saved before handing control back")
            self._detach(access)
            if not self._accesses:
                self.session.stop(shutdown=True, force=False)
            return
        access.closing = True
        if len(self._accesses) == 1:
            self.session.stop(shutdown=True, force=False)
        elif self._writer is access:
            access._stop_sequence = self.session.stop(force=False)
        else:
            self._detach(access)


class DeviceAccess:
    """A view's access to a shared controller, not a new serial owner."""
    def __init__(self, controller, purpose):
        self.controller = controller
        self.purpose = purpose
        self.closing = False
        self.closed = False
        self._stop_sequence = None

    @property
    def candidate(self):
        return self.controller.candidate

    @property
    def role(self):
        return self.controller.role

    @property
    def device_id(self):
        return self.controller.session.device_id

    @property
    def alive(self):
        snapshot = self.controller.session.snapshot()
        self.controller._reconcile(snapshot)
        return snapshot["alive"] and not self.closed

    @property
    def writable(self):
        return (self.controller._writer is self and not self.closed and not self.closing
                and self.controller.session.alive)

    def snapshot(self):
        result = self.controller.session.snapshot()
        result["alive"] = result["alive"] and not self.closed
        result["control_available"] = self.writable
        writer = self.controller._writer
        result["control_owner"] = writer.purpose if writer else "none"
        return result

    def request(self, command, payload=None):
        if not self.writable:
            raise ValueError("Device control belongs to another panel; finish or disconnect that session first")
        if command.startswith('setup_') and self.purpose != 'setup':
            raise ValueError("Calibration writes require setup control")
        if command in ('arm','target','calibration') and self.purpose not in ('hardware','session'):
            raise ValueError("Manual motor commands are unavailable during setup")
        controller = self.controller
        snapshot = controller.session.snapshot()
        if command == "connect":
            if controller._connecting or snapshot["state"] in ("connecting", "read-only", "armed", "calibrating"):
                return
            controller._connecting = True
            controller._connect_stop_sequence = snapshot["stop_completed"]
        if command == "arm":
            controller._engage_stop_sequence = snapshot["stop_completed"]
        try:
            controller.session.request(command, payload)
        except Exception:
            if command == "connect":
                controller._connecting = False
            if command == "arm":
                controller._engage_stop_sequence = None
            raise

    def heartbeat(self, held=False):
        self.controller._reconcile(self.controller.session.snapshot())
        if self.writable:
            self.controller.session.heartbeat(held)

    def stop(self, *, disconnect=False, shutdown=False, force=True):
        if shutdown:
            self.controller.release(self)
            return 0
        if not self.writable:
            raise ValueError("Device control belongs to another panel; use that panel's release control")
        return self.controller.session.stop(disconnect=disconnect, force=force)

    def complete_setup(self):
        self.controller.release(self, completed=True)
