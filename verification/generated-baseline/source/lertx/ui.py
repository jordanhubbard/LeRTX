"""Qt presentation layer. PySide6 is imported lazily so portable commands
(``defaults``, ``validate-settings``) never require Qt to be installed.
"""
from __future__ import annotations

import copy
from typing import Callable, Optional

from lertx import config as config_module
from lertx import transport as transport_module
from lertx.simulation import SimulationClock

CHARCOAL_STYLESHEET = """
QMainWindow, QDialog { background-color: #202225; color: #e6e6e6; }
QWidget { background-color: #202225; color: #e6e6e6; font-size: 13px; }
QToolBar { background-color: #262a2d; border: none; spacing: 8px; padding: 6px; }
QDockWidget { titlebar-close-icon: none; }
QTreeWidget, QLineEdit, QDoubleSpinBox, QComboBox, QSpinBox {
    background-color: #2b2f33; border: 1px solid #3a3f44; border-radius: 4px; padding: 4px;
}
QTreeWidget::item:selected, QListWidget::item:selected { background-color: #1f6f6b; }
QPushButton { background-color: #2b2f33; border: 1px solid #3a3f44; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { border-color: #2fa39c; }
QPushButton:focus, QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2fa39c;
}
QLabel#viewport { background-color: #101214; border: 1px solid #3a3f44; }
QStatusBar { background-color: #262a2d; }
"""


def build_application(argv: Optional[list] = None):
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [])
    app.setStyleSheet(CHARCOAL_STYLESHEET)
    return app


def build_main_window(
    initial_profile: dict,
    worker_factory: Callable[[], object],
    default_scene_path: str,
    config_path: str,
):
    """Construct and return the LeRTX main window (real Qt widgets)."""
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QAction, QImage, QPixmap
    from PySide6.QtWidgets import (
        QComboBox,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QDockWidget,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTabWidget,
        QToolBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    class SettingsDialog(QDialog):
        def __init__(self, profile: dict, parent=None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Settings")
            self._staged = copy.deepcopy(profile)
            self._result_profile: Optional[dict] = None

            tabs = QTabWidget(self)
            self._fields: dict = {}
            self._build_general_tab(tabs)
            self._build_rendering_tab(tabs)
            self._build_physics_tab(tabs)
            self._build_devices_tab(tabs)
            self._build_workspace_tab(tabs)
            self._build_intelligence_tab(tabs)
            self._build_diagnostics_tab(tabs)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save
                | QDialogButtonBox.StandardButton.Cancel
                | QDialogButtonBox.StandardButton.RestoreDefaults
            )
            buttons.accepted.connect(self._on_save)
            buttons.rejected.connect(self.reject)
            buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
                self._on_restore_defaults
            )

            layout = QVBoxLayout(self)
            layout.addWidget(tabs)
            layout.addWidget(buttons)

        def _row(self, layout: QFormLayout, label: str, widget, key: str) -> None:
            layout.addRow(label, widget)
            self._fields[key] = widget

        def _build_general_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            theme = QComboBox()
            theme.addItems(["dark", "light"])
            theme.setCurrentText(self._staged["general"]["theme"])
            self._row(layout, "Theme", theme, "general.theme")
            units = QComboBox()
            units.addItems(["m", "cm", "mm"])
            units.setCurrentText(self._staged["general"]["display_units"])
            self._row(layout, "Display units", units, "general.display_units")
            tabs.addTab(page, "General")

        def _build_rendering_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            device = QSpinBox()
            device.setRange(0, 63)
            device.setValue(self._staged["rendering"]["device"])
            self._row(layout, "GPU index", device, "rendering.device")
            width = QSpinBox()
            width.setRange(1, 16384)
            width.setValue(self._staged["rendering"]["width"])
            self._row(layout, "Width", width, "rendering.width")
            height = QSpinBox()
            height.setRange(1, 16384)
            height.setValue(self._staged["rendering"]["height"])
            self._row(layout, "Height", height, "rendering.height")
            fps = QSpinBox()
            fps.setRange(1, 240)
            fps.setValue(self._staged["rendering"]["target_fps"])
            self._row(layout, "Target FPS", fps, "rendering.target_fps")
            quality = QComboBox()
            quality.addItems(["balanced", "high"])
            quality.setCurrentText(self._staged["rendering"]["quality"])
            self._row(layout, "Quality", quality, "rendering.quality")
            note = QLabel("Renderer changes require a confirmed restart.")
            layout.addRow(note)
            tabs.addTab(page, "Rendering")

        def _build_physics_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            timestep = QSpinBox()
            timestep.setRange(1, 2000)
            timestep.setValue(self._staged["physics"]["timestep_hz"])
            self._row(layout, "Timestep (Hz)", timestep, "physics.timestep_hz")
            substeps = QSpinBox()
            substeps.setRange(1, 64)
            substeps.setValue(self._staged["physics"]["substeps"])
            self._row(layout, "Substeps", substeps, "physics.substeps")
            gravity = QLineEdit(self._staged["physics"]["gravity_m_s2"])
            self._row(layout, "Gravity (m/s^2)", gravity, "physics.gravity_m_s2")
            reset_on_edit = QCheckBox()
            reset_on_edit.setChecked(self._staged["physics"]["reset_on_edit"])
            self._row(layout, "Reset on edit", reset_on_edit, "physics.reset_on_edit")
            note = QLabel("Physics changes stop simulation and rebuild without losing authored edits.")
            layout.addRow(note)
            tabs.addTab(page, "Physics")

        def _build_devices_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            discovery = QCheckBox()
            discovery.setChecked(self._staged["devices"]["discovery_enabled"])
            self._row(layout, "Discovery enabled", discovery, "devices.discovery_enabled")
            telemetry = QSpinBox()
            telemetry.setRange(1, 240)
            telemetry.setValue(self._staged["devices"]["telemetry_hz"])
            self._row(layout, "Telemetry (Hz)", telemetry, "devices.telemetry_hz")
            actuation_note = QLabel("Robot actuation is not implemented and cannot be enabled here.")
            layout.addRow(actuation_note)
            tabs.addTab(page, "Devices")

        def _build_workspace_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            paths = QLineEdit(",".join(self._staged["workspace"]["asset_search_paths"]))
            self._row(layout, "Asset search paths (comma separated)", paths, "workspace.asset_search_paths")
            status_note = QLabel(
                "Reconstruction: " + self._staged["workspace"]["reconstruction_status"] + " (unavailable role)"
            )
            layout.addRow(status_note)
            tabs.addTab(page, "Workspace")

        def _build_intelligence_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            endpoint = QLineEdit(self._staged["llm"]["endpoint"])
            self._row(layout, "Endpoint", endpoint, "llm.endpoint")
            model = QLineEdit(self._staged["llm"]["model"])
            self._row(layout, "Model", model, "llm.model")

            key_row = QHBoxLayout()
            self._key_edit = QLineEdit(self._staged["llm"]["api_key"])
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            reveal = QPushButton("Reveal")

            def _toggle_reveal() -> None:
                if self._key_edit.echoMode() == QLineEdit.EchoMode.Password:
                    self._key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                    reveal.setText("Hide")
                else:
                    self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
                    reveal.setText("Reveal")

            reveal.clicked.connect(_toggle_reveal)
            clear_key = QPushButton("Clear")
            clear_key.clicked.connect(lambda: self._key_edit.setText(""))
            key_row.addWidget(self._key_edit)
            key_row.addWidget(reveal)
            key_row.addWidget(clear_key)
            key_widget = QWidget()
            key_widget.setLayout(key_row)
            layout.addRow("API key (session only)", key_widget)
            layout.addRow(QLabel("The API key is kept in memory for this session only and never saved."))
            self._fields["llm.api_key"] = self._key_edit

            tokens = QSpinBox()
            tokens.setRange(1, 131072)
            tokens.setValue(self._staged["llm"]["max_output_tokens"])
            self._row(layout, "Max output tokens", tokens, "llm.max_output_tokens")
            timeout = QSpinBox()
            timeout.setRange(1, 300)
            timeout.setValue(self._staged["llm"]["timeout_seconds"])
            self._row(layout, "Timeout (s)", timeout, "llm.timeout_seconds")

            self._connection_status = QLabel("")
            test_button = QPushButton("Test connection")

            def _on_test() -> None:
                self._connection_status.setText("Testing...")
                result = transport_module.test_connection(
                    endpoint.text(),
                    model.text(),
                    self._key_edit.text(),
                    tokens.value(),
                    timeout.value(),
                )
                self._connection_status.setText(result["state"])

            test_button.clicked.connect(_on_test)
            layout.addRow(test_button, self._connection_status)
            tabs.addTab(page, "Intelligence")

            def _clear_credential_on_endpoint_change(_text: str) -> None:
                self._key_edit.setText("")
                self._connection_status.setText("")

            endpoint.textEdited.connect(_clear_credential_on_endpoint_change)

        def _build_diagnostics_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            layout.addRow("Config directory", QLabel(config_module.user_config_dir()))
            layout.addRow("GPU/SDK status", QLabel("Discovered at native-worker start."))
            tabs.addTab(page, "Diagnostics")

        def _collect_profile(self) -> dict:
            profile = copy.deepcopy(self._staged)
            profile["general"]["theme"] = self._fields["general.theme"].currentText()
            profile["general"]["display_units"] = self._fields["general.display_units"].currentText()
            profile["rendering"]["device"] = self._fields["rendering.device"].value()
            profile["rendering"]["width"] = self._fields["rendering.width"].value()
            profile["rendering"]["height"] = self._fields["rendering.height"].value()
            profile["rendering"]["target_fps"] = self._fields["rendering.target_fps"].value()
            profile["rendering"]["quality"] = self._fields["rendering.quality"].currentText()
            profile["physics"]["timestep_hz"] = self._fields["physics.timestep_hz"].value()
            profile["physics"]["substeps"] = self._fields["physics.substeps"].value()
            profile["physics"]["gravity_m_s2"] = self._fields["physics.gravity_m_s2"].text()
            profile["physics"]["reset_on_edit"] = self._fields["physics.reset_on_edit"].isChecked()
            profile["devices"]["discovery_enabled"] = self._fields["devices.discovery_enabled"].isChecked()
            profile["devices"]["telemetry_hz"] = self._fields["devices.telemetry_hz"].value()
            raw_paths = self._fields["workspace.asset_search_paths"].text()
            profile["workspace"]["asset_search_paths"] = [p for p in raw_paths.split(",") if p]
            profile["llm"]["endpoint"] = self._fields["llm.endpoint"].text()
            profile["llm"]["model"] = self._fields["llm.model"].text()
            profile["llm"]["api_key"] = self._fields["llm.api_key"].text()
            profile["llm"]["max_output_tokens"] = self._fields["llm.max_output_tokens"].value()
            profile["llm"]["timeout_seconds"] = self._fields["llm.timeout_seconds"].value()
            return profile

        def _on_save(self) -> None:
            candidate = self._collect_profile()
            result = config_module.validate_profile(candidate)
            if not result["valid"]:
                QMessageBox.critical(self, "Invalid settings", "\n".join(result["errors"]))
                return
            self._result_profile = candidate
            self.accept()

        def _on_restore_defaults(self) -> None:
            self._staged = copy.deepcopy(config_module.DEFAULT_PROFILE)
            self._result_profile = copy.deepcopy(config_module.DEFAULT_PROFILE)
            self.accept()

        def result_profile(self) -> Optional[dict]:
            return self._result_profile

    class InspectorPanel(QWidget):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._layout = QFormLayout(self)
            self.path_label = QLabel("")
            self.type_label = QLabel("")
            self.translate = [QDoubleSpinBox() for _ in range(3)]
            self.rotate = [QDoubleSpinBox() for _ in range(3)]
            self.scale = [QDoubleSpinBox() for _ in range(3)]
            for spin in self.translate + self.rotate + self.scale:
                spin.setRange(-1_000_000.0, 1_000_000.0)
            self.unsupported_note = QLabel("")
            self.unsupported_note.setVisible(False)

            self._layout.addRow("Path", self.path_label)
            self._layout.addRow("Type", self.type_label)
            self._layout.addRow("Translate (m)", self._triple(self.translate))
            self._layout.addRow("Rotate (deg)", self._triple(self.rotate))
            self._layout.addRow("Scale", self._triple(self.scale))
            self._layout.addRow(self.unsupported_note)
            self.set_enabled_for_selection(False)

        def _triple(self, spins) -> QWidget:
            row = QWidget()
            box = QHBoxLayout(row)
            box.setContentsMargins(0, 0, 0, 0)
            for spin in spins:
                box.addWidget(spin)
            return row

        def set_enabled_for_selection(self, enabled: bool, reason: str = "") -> None:
            for spin in self.translate + self.rotate + self.scale:
                spin.setEnabled(enabled)
            self.unsupported_note.setVisible(not enabled and bool(reason))
            self.unsupported_note.setText(reason)

        def show_prim(self, path: str, prim_type: str, editable: bool, reason: str = "") -> None:
            self.path_label.setText(path)
            self.type_label.setText(prim_type)
            self.set_enabled_for_selection(editable, reason)

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("LeRTX")
            self.resize(1440, 900)

            self.profile = copy.deepcopy(initial_profile)
            self.config_path = config_path
            self.current_scene_path = default_scene_path
            self.has_unsaved_changes = False
            self.worker = None
            self.clock = SimulationClock(self.profile["physics"]["timestep_hz"])

            self._build_toolbar()
            self._build_central_widget()
            self._build_docks()
            self._build_status_bar()

            self._frame_timer = QTimer(self)
            self._frame_timer.timeout.connect(self._on_tick)

        def _build_toolbar(self) -> None:
            toolbar = QToolBar("Main", self)
            self.addToolBar(toolbar)

            open_action = QAction("Open USD", self)
            open_action.triggered.connect(self._on_open)
            toolbar.addAction(open_action)

            save_action = QAction("Save", self)
            save_action.triggered.connect(self._on_save)
            toolbar.addAction(save_action)

            save_as_action = QAction("Save As", self)
            save_as_action.triggered.connect(self._on_save_as)
            toolbar.addAction(save_as_action)

            settings_action = QAction("Settings", self)
            settings_action.triggered.connect(self._on_open_settings)
            toolbar.addAction(settings_action)

            frame_action = QAction("Frame Selection", self)
            frame_action.triggered.connect(self._on_frame_selection)
            toolbar.addAction(frame_action)

        def _build_central_widget(self) -> None:
            central = QWidget()
            layout = QVBoxLayout(central)

            self.viewport_label = QLabel()
            self.viewport_label.setObjectName("viewport")
            self.viewport_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.viewport_label.setMinimumSize(640, 360)
            self.viewport_label.setText("Empty — open a USD scene")
            layout.addWidget(self.viewport_label, stretch=1)

            transport_row = QHBoxLayout()
            self.play_button = QPushButton("Play")
            self.play_button.clicked.connect(self._on_play_pause)
            self.reset_button = QPushButton("Reset")
            self.reset_button.clicked.connect(self._on_reset)
            self.sim_time_label = QLabel("t=0.00s")
            self.frame_rate_label = QLabel("0.0 fps")
            self.native_status_label = QLabel("Native: idle")

            transport_row.addWidget(self.play_button)
            transport_row.addWidget(self.reset_button)
            transport_row.addWidget(self.sim_time_label)
            transport_row.addWidget(self.frame_rate_label)
            transport_row.addWidget(self.native_status_label)
            transport_row.addStretch(1)
            layout.addLayout(transport_row)

            self.setCentralWidget(central)

        def _build_docks(self) -> None:
            hierarchy_dock = QDockWidget("Scene", self)
            hierarchy_widget = QWidget()
            hierarchy_layout = QVBoxLayout(hierarchy_widget)
            self.search_edit = QLineEdit()
            self.search_edit.setPlaceholderText("Search hierarchy")
            self.search_edit.textEdited.connect(self._on_search_changed)
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Prim"])
            self.tree.itemSelectionChanged.connect(self._on_selection_changed)
            hierarchy_layout.addWidget(self.search_edit)
            hierarchy_layout.addWidget(self.tree)
            hierarchy_dock.setWidget(hierarchy_widget)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, hierarchy_dock)

            inspector_dock = QDockWidget("Inspector", self)
            self.inspector = InspectorPanel()
            inspector_dock.setWidget(self.inspector)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, inspector_dock)

        def _build_status_bar(self) -> None:
            self.setStatusBar(QStatusBar())

        def _on_search_changed(self, text: str) -> None:
            lowered = text.lower()
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                item.setHidden(bool(lowered) and lowered not in item.text(0).lower())

        def _on_selection_changed(self) -> None:
            items = self.tree.selectedItems()
            if not items:
                self.inspector.set_enabled_for_selection(False)
                return
            item = items[0]
            path = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
            self.inspector.show_prim(path, "Xform", True)

        def _confirm_discard_if_dirty(self) -> bool:
            if not self.has_unsaved_changes:
                return True
            box = QMessageBox(self)
            box.setWindowTitle("Unsaved changes")
            box.setText("This scene has unsaved changes.")
            box.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            choice = box.exec()
            if choice == QMessageBox.StandardButton.Cancel:
                return False
            if choice == QMessageBox.StandardButton.Save:
                self._on_save()
            return True

        def _on_open(self) -> None:
            if not self._confirm_discard_if_dirty():
                return
            path, _ = QFileDialog.getOpenFileName(self, "Open USD", "", "USD (*.usd *.usda *.usdc)")
            if not path:
                return
            self.open_scene(path)

        def open_scene(self, path: str) -> None:
            self.current_scene_path = path
            self.has_unsaved_changes = False
            self._start_native_worker()

        def _on_save(self) -> None:
            self.has_unsaved_changes = False

        def _on_save_as(self) -> None:
            path, _ = QFileDialog.getSaveFileName(self, "Save USD As", "", "USD (*.usd *.usda *.usdc)")
            if not path:
                return
            self.current_scene_path = path
            self._on_save()

        def _on_open_settings(self) -> None:
            dialog = SettingsDialog(self.profile, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_profile = dialog.result_profile()
                if new_profile is not None:
                    restart_needed = (
                        new_profile["rendering"] != self.profile["rendering"]
                    )
                    physics_changed = new_profile["physics"] != self.profile["physics"]
                    config_module.save_profile(new_profile, self.config_path)
                    self.profile = new_profile
                    self.clock.set_timestep_hz(self.profile["physics"]["timestep_hz"])
                    if physics_changed:
                        self.clock.pause()
                        self.clock.reset()
                    if restart_needed:
                        self.native_status_label.setText("Native: restart required")

        def _on_frame_selection(self) -> None:
            self.native_status_label.setText("Native: framing selection")

        def _on_play_pause(self) -> None:
            if self.clock.playing:
                self.clock.pause()
                self.play_button.setText("Play")
            else:
                self.clock.play()
                self.play_button.setText("Pause")

        def _on_reset(self) -> None:
            self.clock.pause()
            self.clock.reset()
            self.play_button.setText("Play")
            self.sim_time_label.setText("t=0.00s")

        def _start_native_worker(self) -> None:
            try:
                self.worker = worker_factory()
                self.worker.set_error_handler(self._on_worker_error)
                self.worker.start()
                self.native_status_label.setText("Native: ready")
                self._frame_timer.start(int(1000 / max(self.profile["rendering"]["target_fps"], 1)))
            except Exception as exc:  # noqa: BLE001
                self.native_status_label.setText(f"Native: unavailable ({exc})")

        def _on_worker_error(self, exc: Exception) -> None:
            self.native_status_label.setText(f"Native: error ({exc})")
            self._frame_timer.stop()

        def _on_tick(self) -> None:
            self.sim_time_label.setText(f"t={self.clock.sim_time:.2f}s")

        def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
            if not self._confirm_discard_if_dirty():
                event.ignore()
                return
            self._frame_timer.stop()
            if self.worker is not None:
                self.worker.stop()
                self.worker = None
            event.accept()

    return MainWindow()
