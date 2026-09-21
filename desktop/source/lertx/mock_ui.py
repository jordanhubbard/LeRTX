"""Explicit simulated telemetry panel. No USB or robot configuration is touched."""
from .telemetry import JOINTS, ROLES, LatestSample, MockReader


def build_mock_dialog(parent=None):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (QCheckBox, QDialog, QDoubleSpinBox, QFormLayout,
                                  QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

    class MockDialog(QDialog):
        def __init__(self):
            super().__init__(parent)
            self.setWindowTitle("SIMULATED — leader/follower telemetry")
            self.resize(800, 550)
            self.readers, self.streams, self.controls, self.statuses = {}, {}, {}, {}
            layout = QVBoxLayout(self)
            warning = QLabel("SIMULATED TEST INPUTS — no hardware connection, calibration, motor writes or "
                             "rendered robot synchronization. Input ranges are mock controls, not physical limits.")
            warning.setWordWrap(True)
            layout.addWidget(warning)
            columns = QHBoxLayout()
            layout.addLayout(columns)
            for role in ROLES:
                reader = MockReader(role)
                self.readers[role] = reader
                self.streams[role] = LatestSample(reader.source, role)
                group = QGroupBox(role.capitalize() + " (simulated)")
                form = QFormLayout(group)
                connected = QCheckBox("Connect mock")
                connected.toggled.connect(lambda value, role=role: self.connect_role(role, value))
                form.addRow(connected)
                frozen = QCheckBox("Freeze stream (stale after 1 second)")
                frozen.toggled.connect(lambda value, reader=reader: setattr(reader, "frozen", value))
                form.addRow(frozen)
                joints = []
                for name in JOINTS:
                    control = QDoubleSpinBox()
                    control.setRange(-180, 180)
                    control.setSuffix(" deg")
                    form.addRow(name.replace("_", " ").capitalize(), control)
                    joints.append(control)
                gripper = QDoubleSpinBox()
                gripper.setRange(0, 100)
                gripper.setValue(50)
                gripper.setSuffix(" %")
                form.addRow("Gripper", gripper)
                status = QLabel("SIMULATED — disconnected")
                status.setWordWrap(True)
                form.addRow(status)
                self.controls[role] = (connected, frozen, joints, gripper)
                self.statuses[role] = status
                columns.addWidget(group)
            close = QPushButton("Close")
            close.clicked.connect(self.reject)
            layout.addWidget(close)
            self.timer = QTimer(self)
            self.timer.setInterval(33)
            self.timer.timeout.connect(self.poll)
            self.timer.start()
            self.finished.connect(self.finish)

        def connect_role(self, role, connected):
            if connected:
                self.readers[role].connect()
                self.streams[role].connect()
            else:
                self.readers[role].disconnect()
                self.streams[role].disconnect()
            self.poll()

        def poll(self):
            for role in ROLES:
                reader, stream = self.readers[role], self.streams[role]
                _, _, joints, gripper = self.controls[role]
                reader.set_pose([control.value() for control in joints], gripper.value())
                sample = reader.read()
                if sample is not None:
                    stream.accept(sample)
                latest = stream.latest
                detail = ("\nLast received: " + ", ".join(f"{v:.1f}" for v in latest.degrees)
                          + f" deg; gripper {latest.gripper_percent:.1f}%; sample {latest.sequence}") if latest else ""
                self.statuses[role].setText("SIMULATED — " + stream.state + detail)

        def finish(self, *_):
            self.timer.stop()
            for role in ROLES:
                self.readers[role].disconnect()
                self.streams[role].disconnect()

    return MockDialog()
