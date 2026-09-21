"""Read-only telemetry boundary and deterministic, hardware-free test backend."""
from dataclasses import dataclass
import math
import time
from typing import Protocol

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")
ROLES = ("leader", "follower")


@dataclass(frozen=True)
class Sample:
    source: str
    role: str
    sequence: int
    timestamp: float
    degrees: tuple[float, ...]
    gripper_percent: float


class ReadOnlyReader(Protocol):
    def connect(self) -> None: ...
    def read(self) -> Sample | None: ...
    def disconnect(self) -> None: ...


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class LatestSample:
    def __init__(self, source, role, stale_after=1.0, clock=time.monotonic):
        if role not in ROLES or not isinstance(source, str) or not source:
            raise ValueError("Invalid telemetry identity")
        if not _finite(stale_after) or stale_after <= 0:
            raise ValueError("Invalid stale threshold")
        self.source, self.role = source, role
        self.stale_after, self.clock = stale_after, clock
        self.latest = None
        self.connected = False

    def connect(self):
        self.latest = None
        self.connected = True

    def disconnect(self):
        self.connected = False

    def accept(self, sample):
        now = self.clock()
        valid = (self.connected and isinstance(sample, Sample)
                 and sample.source == self.source and sample.role == self.role
                 and type(sample.sequence) is int and sample.sequence >= 0
                 and _finite(sample.timestamp) and sample.timestamp <= now
                 and isinstance(sample.degrees, tuple) and len(sample.degrees) == len(JOINTS)
                 and all(_finite(v) for v in sample.degrees)
                 and _finite(sample.gripper_percent) and 0 <= sample.gripper_percent <= 100)
        if not valid:
            raise ValueError("Invalid telemetry sample")
        if self.latest and (sample.sequence <= self.latest.sequence
                            or sample.timestamp < self.latest.timestamp):
            raise ValueError("Out-of-order telemetry sample")
        self.latest = sample

    @property
    def state(self):
        if not self.connected:
            return "disconnected"
        if self.latest is None:
            return "awaiting sample"
        return "stale" if self.clock()-self.latest.timestamp >= self.stale_after else "live"


class MockReader:
    """Explicit synthetic inputs only; no physical connection or calibration."""
    def __init__(self, role, clock=time.monotonic):
        if role not in ROLES:
            raise ValueError("Invalid mock role")
        self.role, self.clock = role, clock
        self.source = "mock:so101:" + role
        self.connected = False
        self.frozen = False
        self.sequence = 0
        self.degrees = (0.0,) * len(JOINTS)
        self.gripper_percent = 50.0

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def set_pose(self, degrees, gripper_percent):
        if (len(degrees) != len(JOINTS) or not all(_finite(v) and -180 <= v <= 180 for v in degrees)
                or not _finite(gripper_percent) or not 0 <= gripper_percent <= 100):
            raise ValueError("Invalid mock input")
        self.degrees, self.gripper_percent = tuple(degrees), gripper_percent

    def read(self):
        if not self.connected or self.frozen:
            return None
        self.sequence += 1
        return Sample(self.source, self.role, self.sequence, self.clock(),
                      self.degrees, self.gripper_percent)
