"""Non-actuating USB candidate panel; telemetry readiness is never implied."""
from .devices import ROLES, RoleAssignments


def build_devices_dialog(profile, probe, roles_path, parent=None):
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,QComboBox,QGroupBox,QScrollArea,QWidget,QTabWidget

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
            outer=QVBoxLayout(self);tabs=QTabWidget();outer.addWidget(tabs,1)
            scroll=QScrollArea(self);scroll.setWidgetResizable(True)
            content=QWidget();scroll.setWidget(content);tabs.addTab(scroll,'Robot arms')
            layout = QVBoxLayout(content)
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
            self.calibrate_buttons = {}
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
                calibrate=QPushButton("Calibrate "+role.title())
                calibrate.clicked.connect(lambda checked=False,role=role:self.calibrate(role))
                self.calibrate_buttons[role]=calibrate;layout.addWidget(calibrate)
            self.scan_button = QPushButton("Scan now")
            self.scan_button.clicked.connect(self.scan)
            layout.addWidget(self.scan_button)
            camera=getattr(parent,'camera_service',None)
            if camera:
                from .camera import CameraPreview
                group=QGroupBox('USB camera · select by live preview');camera_layout=QVBoxLayout(group)
                self.camera_combo=QComboBox();camera_layout.addWidget(self.camera_combo)
                self.camera_status=QLabel();self.camera_status.setWordWrap(True);camera_layout.addWidget(self.camera_status)
                row=QHBoxLayout();camera_layout.addLayout(row)
                preview=QPushButton('Preview selected camera');preview.clicked.connect(self.preview_camera);row.addWidget(preview)
                use=QPushButton('Use this camera');use.clicked.connect(self.use_camera);row.addWidget(use)
                self.camera_preview=CameraPreview(camera,self,hide_disabled=False)
                camera_layout.addWidget(self.camera_preview,1)
                tabs.addTab(group,'USB camera')
                self.camera_ids=[];camera.changed.connect(self.refresh_cameras);self.refresh_cameras()
                self.resize(1000,720)
            layout=outer
            if parent and hasattr(parent,"open_robot_session"):
                session=QPushButton("Robot session · record, follow and replay")
                session.clicked.connect(self.open_session);layout.addWidget(session)
            self.mock_button = QPushButton("Open telemetry mock (no hardware)")
            self.mock_button.clicked.connect(self.open_mock)
            layout.addWidget(self.mock_button)
            close = QPushButton("Back to scene")
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

        def open_session(self):
            if parent.open_robot_session(session_assignments=dict(self.roles.session) if self.roles else {}):self.accept()

        def refresh_cameras(self):
            camera=parent.camera_service;devices=camera.devices();ids=[d['id'] for d in devices]
            if ids!=self.camera_ids:
                previous=self.camera_combo.currentData() or camera.selected_id
                self.camera_ids=ids;self.camera_combo.clear()
                for d in devices:self.camera_combo.addItem(d['name']+(' · session-only' if not d.get('persistent',True) else ''),d['id'])
                index=self.camera_combo.findData(previous)
                self.camera_combo.setCurrentIndex(index if previous else (0 if devices else -1))
            self.camera_status.setText(camera.status+(' · saved camera disconnected' if camera.selected_id and camera.selected_id not in ids else ''))

        def preview_camera(self):
            try:parent.camera_service.preview(self.camera_combo.currentData())
            except (ValueError,OSError) as exc:self.camera_status.setText(str(exc))

        def use_camera(self):
            try:parent.camera_service.use_camera(self.camera_combo.currentData())
            except (ValueError,OSError) as exc:self.camera_status.setText(str(exc))

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

        def calibrate(self,role):
            if not self.roles or not self.last_scan_ok:return
            state,candidate=self.roles.resolve(role,self.candidates)
            if state=='assigned' and parent and hasattr(parent,'open_setup'):
                if parent.open_setup(role=role,candidate=candidate) is not False:self.accept()
                else:self.status.setText(parent.statusBar().currentMessage())

        def active_sessions(self):
            registry=getattr(parent,'devices',None)
            return [c.session for c in registry.active_controllers()] if registry else []

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
                self.calibrate_buttons[role].setEnabled(assigned and self.last_scan_ok)
                self.calibrate_buttons[role].setText('Calibrate '+role.title()+(' · '+candidate.port if candidate else ''))
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
