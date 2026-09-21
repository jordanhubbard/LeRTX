"""USB metadata discovery and conservative role assignment. Never opens ports."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

ROLES = ("leader", "follower")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate role configuration key")
        result[key] = value
    return result


@dataclass(frozen=True)
class Candidate:
    port: str
    vendor: int
    product: int
    serial: str = ""
    description: str = "USB serial candidate"

    @property
    def identity(self):
        if not self.serial:
            return None
        value = json.dumps([self.vendor, self.product, self.serial], ensure_ascii=True)
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @property
    def attachment(self):
        return (self.port, self.vendor, self.product, self.serial)


def scan_candidates():
    from PySide6.QtSerialPort import QSerialPortInfo
    result = []
    for port in QSerialPortInfo.availablePorts():
        if port.hasVendorIdentifier() and port.hasProductIdentifier():
            result.append(Candidate(port.systemLocation(), port.vendorIdentifier(),
                port.productIdentifier(), port.serialNumber(), port.description()))
    return sorted(result, key=lambda candidate: candidate.port)


def scan_result(cancel_token=None):
    try:
        candidates = scan_candidates()
        return {"state":"success", "candidates": candidates}
    except Exception:
        return {"state":"scan_failed"}


class RoleAssignments:
    def __init__(self, filename):
        self.filename = Path(filename)
        self.persistent = {}
        self.session = {}
        if self.filename.exists():
            with self.filename.open("rb") as stream:
                raw = stream.read(65537)
            try:
                if len(raw) > 65536:
                    raise ValueError()
                value = json.loads(raw, object_pairs_hook=_unique_pairs)
                if not isinstance(value, dict) or set(value) != {"schema", "roles"} or type(value["schema"]) is not int or value["schema"] != 1:
                    raise ValueError()
                roles = value["roles"]
                if not isinstance(roles, dict) or not set(roles) <= set(ROLES):
                    raise ValueError()
                if any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v) for v in roles.values()):
                    raise ValueError()
                if len(set(roles.values())) != len(roles):
                    raise ValueError()
                self.persistent = roles
            except (ValueError, UnicodeError, RecursionError):
                raise ValueError("Invalid device role configuration; file preserved") from None

    def update(self, candidates):
        attached = {candidate.attachment for candidate in candidates}
        self.session = {role: identity for role, identity in self.session.items() if identity in attached}

    def resolve(self, role, candidates):
        if role not in ROLES:
            raise ValueError("Unknown device role")
        if role in self.session:
            matches = [c for c in candidates if c.attachment == self.session[role]]
        elif role in self.persistent:
            matches = [c for c in candidates if c.identity == self.persistent[role]]
        else:
            return "unassigned", None
        if len(matches) == 1:
            return "assigned", matches[0]
        return ("ambiguous" if matches else "missing"), None

    def _save(self, roles):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".lertx-devices-", suffix=".json", dir=self.filename.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"schema":1,"roles":roles}, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def assign(self, role, candidate, candidates):
        if role not in ROLES or candidate not in candidates:
            raise ValueError("Choose a currently attached candidate and valid role")
        for other in ROLES:
            if other != role:
                if candidate.identity and self.persistent.get(other) == candidate.identity:
                    raise ValueError("Unassign the other role before reusing its USB identity")
                _, assigned = self.resolve(other, candidates)
                if assigned is not None and assigned.port == candidate.port:
                    raise ValueError("Unassign the other role before reusing this port")
        unique = candidate.identity is not None and Counter(c.identity for c in candidates)[candidate.identity] == 1
        persistent, session = dict(self.persistent), dict(self.session)
        persistent.pop(role, None)
        session.pop(role, None)
        if unique:
            persistent[role] = candidate.identity
        else:
            session[role] = candidate.attachment
        self._save(persistent)
        self.persistent, self.session = persistent, session
        return "persistent" if unique else "session-only"

    def unassign(self, role):
        if role not in ROLES:
            raise ValueError("Unknown device role")
        persistent = dict(self.persistent)
        persistent.pop(role, None)
        self._save(persistent)
        self.persistent = persistent
        self.session.pop(role, None)
