"""Non-actuating USB candidate panel; telemetry readiness is never implied."""
from .devices import ROLES, RoleAssignments


def build_devices_dialog(profile, probe, roles_path, parent=None):
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout

    from .role_ui import widgets,role_icon
    QLabel,QPushButton,QCheckBox=widgets(lambda: parent.profile if parent and hasattr(parent,'profile') else profile)

    class DevicesDialog(QDialog):
        def __init__(self):
            super().__init__(parent)
            self.setWindowTitle("USB devices and roles")
            self.resize(850, 500)
            self.candidates = []
            self.ticket = None
            self.active = True
            self.last_scan_ok = False
            layout = QVBoxLayout(self)
            note = QLabel("Metadata discovery does not open serial ports. Candidates are not yet verified SO-101 robots. "
                          "Assign leader/follower explicitly. Unique USB serial identities are remembered; ambiguous "
                          "or absent serial IDs are session-only and cleared when disconnected or this panel closes. "
                          "Open a hardware panel for explicit read-only connection, calibration and manual motor controls.")
            note.setWordWrap(True)
            layout.addWidget(note)
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Port", "Description", "USB ID", "Serial", "Identity", "Role"])
            from PySide6.QtCore import QSize
            self.tree.setIconSize(QSize(20,20))
            layout.addWidget(self.tree)
            self.status = QLabel("Not scanned")
            self.status.setTextFormat(Qt.TextFormat.PlainText)
            self.status.setWordWrap(True)
            layout.addWidget(self.status)
            self.role_labels = {}
            self.assignment_note=QLabel();self.assignment_note.setWordWrap(True);layout.addWidget(self.assignment_note)
            self.assign_buttons = {}
            self.clear_buttons = {}
            self.hardware_buttons = {}
            for role in ROLES:
                row = QHBoxLayout()
                label = QLabel(role + ": unassigned")
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setWordWrap(True)
                self.role_labels[role] = label
                row.addWidget(label)
                button = QPushButton("Assign " + role)
                button.clicked.connect(lambda checked=False, role=role: self.assign(role))
                self.assign_buttons[role] = button
                row.addWidget(button)
                clear = QPushButton("Unassign " + role)
                clear.clicked.connect(lambda checked=False, role=role: self.unassign(role))
                self.clear_buttons[role] = clear
                row.addWidget(clear)
                hardware=QPushButton('Open '+role+' controls')
                hardware.setIconSize(QSize(20,20))
                hardware.clicked.connect(lambda checked=False,role=role:self.open_hardware(role))
                self.hardware_buttons[role]=hardware;row.addWidget(hardware)
                layout.addLayout(row)
            self.scan_button = QPushButton("Scan now")
            self.scan_button.clicked.connect(self.scan)
            layout.addWidget(self.scan_button)
            self.mock_button = QPushButton("Open telemetry mock (no hardware)")
            self.mock_button.clicked.connect(self.open_mock)
            layout.addWidget(self.mock_button)
            close = QPushButton("Close")
            close.clicked.connect(self.reject)
            layout.addWidget(close)
            self.config_error = ""
            try:
                self.roles = RoleAssignments(roles_path)
            except (OSError, ValueError):
                self.roles = None
                self.config_error = "Device role configuration could not be read; file preserved."
            self.tree.itemSelectionChanged.connect(self.refresh_roles)
            self.timer = QTimer(self)
            self.timer.setInterval(50)
            self.timer.timeout.connect(self.poll)
            self.rescan = QTimer(self)
            self.rescan.setInterval(1000)
            self.rescan.timeout.connect(self.scan)
            if profile["devices"]["discovery_enabled"]:
                self.rescan.start()
            self.finished.connect(self.finish)
            self.refresh_roles()
            self.scan()

        def open_mock(self):
            from .mock_ui import build_mock_dialog
            dialog = build_mock_dialog(self)
            dialog.exec()
            dialog.deleteLater()

        def open_hardware(self,role):
            if not self.roles or not self.last_scan_ok:return
            state,candidate=self.roles.resolve(role,self.candidates)
            if state=='assigned' and parent and hasattr(parent,'open_hardware'):
                if parent.open_hardware(candidate,role) is not False:self.accept()
                else:self.status.setText(parent.statusBar().currentMessage())

        def active_sessions(self):
            return [p.session for p in getattr(parent,'_hardware_windows',{}).values()
                if getattr(p,'session',None) and p.session._thread.is_alive()]

        def selected(self):
            item = self.tree.currentItem()
            return item.data(0, Qt.ItemDataRole.UserRole) if item else None

        def refresh_roles(self):
            selected = self.selected()
            sessions=self.active_sessions()
            palette=parent.profile if parent and hasattr(parent,'profile') else profile
            self.assignment_note.setText('Close hardware controls and setup windows before changing device roles.' if sessions else
                'Select a device row, then assign its role. Each control button names its role and USB port.')
            from PySide6.QtGui import QIcon
            for i in range(self.tree.topLevelItemCount()):
                item=self.tree.topLevelItem(i);item.setText(5,'Unassigned');item.setIcon(5,QIcon())
            for role in ROLES:
                candidate=None
                if self.roles is None:
                    message = "configuration unavailable"
                else:
                    state, candidate = self.roles.resolve(role, self.candidates)
                    active=next((s for s in sessions if candidate and s.candidate.attachment==candidate.attachment),None)
                    message = candidate.port + " (unverified; telemetry disconnected)" if candidate else state
                    if active:
                        message=candidate.port+' · '+(active.snapshot()['state'] if active.role==role else 'open as '+active.role+' — close old controls')
                    if role in self.roles.session:
                        message += " — session-only"
                    if not self.last_scan_ok:
                        message += " — discovery unknown"
                self.role_labels[role].setText(role.title() + ": " + message)
                self.role_labels[role].setStyleSheet('font-weight: bold; padding: 6px;')
                self.assign_buttons[role].setEnabled(self.roles is not None and selected is not None and self.last_scan_ok and not sessions)
                self.clear_buttons[role].setEnabled(self.roles is not None and not sessions)
                assigned=self.roles.resolve(role,self.candidates)[0]=='assigned' if self.roles else False
                self.hardware_buttons[role].setEnabled(assigned and self.last_scan_ok)
                self.hardware_buttons[role].setText('Open '+role.title()+' controls'+(' · '+candidate.port if candidate else ''))
                for i in range(self.tree.topLevelItemCount()):
                    item=self.tree.topLevelItem(i)
                    if candidate and item.data(0,Qt.ItemDataRole.UserRole).attachment==candidate.attachment:
                        item.setText(5,role.title());item.setIcon(5,role_icon(role,palette))

        def scan(self):
            if not self.active or self.ticket is not None:
                return
            self.ticket = probe.start(())
            if self.ticket is None:
                self.status.setText("An earlier scan is still finishing; retry shortly.")
                return
            self.scan_button.setEnabled(False)
            self.timer.start()

        def poll(self):
            if not self.active or self.ticket is None:
                return
            result = probe.poll(self.ticket)
            if result is None:
                return
            self.timer.stop()
            self.ticket = None
            self.scan_button.setEnabled(True)
            self.last_scan_ok = result.get("state") == "success"
            if not self.last_scan_ok:
                self.status.setText("USB enumeration failed; connection state unknown. " + self.config_error)
                # An observation gap cannot preserve identity-less attachments.
                if self.roles:
                    self.roles.session.clear()
                self.refresh_roles()
                return
            previous = self.selected()
            self.candidates = result["candidates"]
            if self.roles:
                self.roles.update(self.candidates)
            self.tree.clear()
            for candidate in self.candidates:
                unique = candidate.identity and sum(c.identity == candidate.identity for c in self.candidates) == 1
                item = QTreeWidgetItem([candidate.port, candidate.description,
                    f"{candidate.vendor:04x}:{candidate.product:04x}", candidate.serial or "none",
                    "unique serial" if unique else "session-only"])
                item.setData(0, Qt.ItemDataRole.UserRole, candidate)
                self.tree.addTopLevelItem(item)
                if previous and previous.attachment == candidate.attachment:
                    self.tree.setCurrentItem(item)
            self.status.setText((f"{len(self.candidates)} unverified USB serial candidate(s). " if self.candidates
                                 else "No USB serial candidates attached. ") + self.config_error)
            self.refresh_roles()

        def assign(self, role):
            if self.active_sessions():
                self.status.setText('Close hardware controls and setup windows before changing device roles.');return
            candidate = self.selected()
            if self.roles is None or candidate is None or not self.last_scan_ok:
                return
            try:
                mode = self.roles.assign(role, candidate, self.candidates)
                self.status.setText(f"Assigned {role} ({mode}); no port opened or motor commands sent.")
            except (ValueError, OSError):
                self.status.setText(
                    f"Could not assign {role}: this device may already be assigned to another role, or the "
                    "device role file could not be written. Unassign the conflicting role, or check that "
                    f"{roles_path} is writable, then try again.")
            self.refresh_roles()

        def unassign(self, role):
            if self.active_sessions():
                self.status.setText('Close hardware controls and setup windows before changing device roles.');return
            if self.roles is not None:
                try:
                    self.roles.unassign(role)
                except (ValueError, OSError):
                    self.status.setText("Could not save role change; previous assignments retained.")
                self.refresh_roles()

        def finish(self, *_):
            self.active = False
            self.timer.stop()
            self.rescan.stop()
            if self.ticket is not None:
                probe.cancel(self.ticket)
            if self.roles:
                self.roles.session.clear()

    return DevicesDialog()
