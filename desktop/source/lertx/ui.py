"""Qt presentation layer. PySide6 is imported lazily so portable commands
(``defaults``, ``validate-settings``) never require Qt to be installed.
"""
from __future__ import annotations

import copy
import time
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
    from .branding import configure_application
    configure_application(app)
    app.setStyleSheet(CHARCOAL_STYLESHEET)
    return app


def build_main_window(
    initial_profile: dict,
    worker_factory: Callable[[], object],
    default_scene_path: str,
    config_path: str,
):
    """Construct and return the LeRTX main window (real Qt widgets)."""
    from PySide6.QtCore import Qt, QTimer, Signal
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
        QProgressBar,
        QPushButton,
        QSpinBox,
        QSizePolicy,
        QStatusBar,
        QTabWidget,
        QToolBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    from .role_ui import widgets, dot
    role_profile=[initial_profile]
    QLabel,QPushButton,QCheckBox=widgets(lambda:role_profile[0])

    class SettingsDialog(QDialog):
        def __init__(self, profile: dict, parent=None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Settings")
            self._staged = copy.deepcopy(profile)
            self._result_profile: Optional[dict] = None
            self._probe = parent.connection_probe
            self._probe_ticket = None
            self.finished.connect(lambda _: self._cancel_probe())
            self._probe_timer = QTimer(self)
            self._probe_timer.timeout.connect(self._poll_probe)

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
            self._validation_label = QLabel("")
            self._validation_label.setWordWrap(True)
            layout.addWidget(self._validation_label)
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

        PROVIDER_PRESETS = {
            "NVIDIA": ("https://inference-api.nvidia.com/v1/responses", "azure/openai/gpt-6-astra"),
            "OpenAI": ("https://api.openai.com/v1/responses", "gpt-5"),
            "OpenRouter": ("https://openrouter.ai/api/v1/responses", "openai/gpt-5-mini"),
        }

        def _build_intelligence_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)

            provider = QComboBox()
            provider.addItems(list(self.PROVIDER_PRESETS) + ["Custom"])
            note = QLabel(
                "Presets fill in a known-working endpoint and model; edit them afterward if you like. "
                "Only OpenAI Responses-API-compatible endpoints work here — many providers (e.g. Anthropic) "
                "use a different API shape and need Custom with a compatible gateway such as OpenRouter.")
            note.setWordWrap(True)
            layout.addRow("Provider", provider)
            layout.addRow(note)
            endpoint = QLineEdit(self._staged["llm"]["endpoint"])
            self._row(layout, "Endpoint", endpoint, "llm.endpoint")
            model = QLineEdit(self._staged["llm"]["model"])
            self._row(layout, "Model", model, "llm.model")

            def _sync_provider_from_fields():
                current = (endpoint.text(), model.text())
                for name, preset in self.PROVIDER_PRESETS.items():
                    if current == preset:
                        provider.blockSignals(True); provider.setCurrentText(name); provider.blockSignals(False)
                        return
                provider.blockSignals(True); provider.setCurrentText("Custom"); provider.blockSignals(False)

            def _apply_provider(name):
                preset = self.PROVIDER_PRESETS.get(name)
                if preset:
                    endpoint.setText(preset[0])
                    model.setText(preset[1])
                    _clear_credential_on_endpoint_change(preset[0])

            provider.currentTextChanged.connect(_apply_provider)
            self._sync_provider_from_fields = _sync_provider_from_fields
            self._provider_combo = provider
            _sync_provider_from_fields()

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
                validation = config_module.validate_profile(self._collect_profile())
                if not validation["valid"]:
                    self._validation_label.setText("Invalid: " + ", ".join(validation["errors"]))
                    return
                self._cancel_probe()
                self._probe_ticket = self._probe.start((endpoint.text(), model.text(),
                    self._key_edit.text(), tokens.value(), timeout.value()))
                if self._probe_ticket is None:
                    self._connection_status.setText("Previous request is finishing; retry shortly")
                    return
                self._connection_status.setText("Testing...")
                self._probe_timer.start(30)

            test_button.clicked.connect(_on_test)
            layout.addRow(test_button, self._connection_status)
            tabs.addTab(page, "Intelligence")

            def _clear_credential_on_endpoint_change(_text: str) -> None:
                self._cancel_probe()
                self._key_edit.setText("")
                self._connection_status.setText("")

            endpoint.textEdited.connect(_clear_credential_on_endpoint_change)
            endpoint.textEdited.connect(lambda _: _sync_provider_from_fields())
            model.textEdited.connect(lambda _: _sync_provider_from_fields())
            for field in (model, self._key_edit):
                field.textChanged.connect(lambda _: self._invalidate_connection())
            tokens.valueChanged.connect(lambda _: self._invalidate_connection())
            timeout.valueChanged.connect(lambda _: self._invalidate_connection())

        def _cancel_probe(self):
            self._probe_timer.stop()
            if self._probe_ticket is not None:
                self._probe.cancel(self._probe_ticket)
                self._probe_ticket = None

        def _invalidate_connection(self):
            self._cancel_probe()
            self._connection_status.setText("")

        def _poll_probe(self):
            result = self._probe.poll(self._probe_ticket)
            if result is not None:
                self._probe_timer.stop()
                self._connection_status.setText(result["state"])

        def _build_diagnostics_tab(self, tabs: QTabWidget) -> None:
            page = QWidget()
            layout = QFormLayout(page)
            layout.addRow("Config directory", QLabel(config_module.user_config_dir()))
            diagnostics = getattr(self.parent(), "_diagnostics", {})
            if diagnostics:
                for name, value in diagnostics.items():
                    label = QLabel(str(value))
                    label.setWordWrap(True)
                    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    layout.addRow(name, label)
            else:
                layout.addRow("GPU/SDK status", QLabel("Not initialized. Open a scene to discover native runtime details."))
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
                self._validation_label.setText("Invalid: " + ", ".join(result["errors"]))
                return
            self._result_profile = candidate
            self.accept()

        def _on_restore_defaults(self) -> None:
            self._cancel_probe()
            self._staged = copy.deepcopy(config_module.DEFAULT_PROFILE)
            for name, widget in self._fields.items():
                section, key = name.split(".")
                value = self._staged[section][key]
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QSpinBox):
                    widget.setValue(value)
                else:
                    widget.setText(",".join(value) if isinstance(value, list) else str(value))
            if hasattr(self, "_sync_provider_from_fields"):
                self._sync_provider_from_fields()
            self._validation_label.setText("Defaults staged. Save to apply, or Cancel to discard.")

        def result_profile(self) -> Optional[dict]:
            return self._result_profile

    class InspectorPanel(QWidget):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._layout = QFormLayout(self)
            self.path_label = QLabel("")
            self.type_label = QLabel("")
            self.path_label.setTextFormat(Qt.TextFormat.PlainText)
            self.path_label.setWordWrap(True)
            self.type_label.setTextFormat(Qt.TextFormat.PlainText)
            self.translate = [QDoubleSpinBox() for _ in range(3)]
            self.rotate = [QDoubleSpinBox() for _ in range(3)]
            self.scale = [QDoubleSpinBox() for _ in range(3)]
            for spin in self.translate + self.rotate + self.scale:
                spin.setRange(-1_000_000.0, 1_000_000.0)
                spin.setDecimals(5)
                spin.setMinimumWidth(spin.fontMetrics().horizontalAdvance("-1000000.00000") + 44)
                spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.unsupported_note = QLabel("")
            self.unsupported_note.setVisible(False)

            self._layout.addRow("Path", self.path_label)
            self._layout.addRow("Type", self.type_label)
            self.translate_label = QLabel("Translate (m)")
            self._layout.addRow(self.translate_label, self._triple(self.translate))
            self._layout.addRow("Rotate (deg)", self._triple(self.rotate))
            self._layout.addRow("Scale", self._triple(self.scale))
            self._layout.addRow(self.unsupported_note)
            self.apply_button = QPushButton("Apply transform")
            self._layout.addRow(self.apply_button)
            self.set_enabled_for_selection(False)

        def _triple(self, spins) -> QWidget:
            row = QWidget()
            box = QVBoxLayout(row)
            box.setContentsMargins(0, 0, 0, 0)
            for axis, spin in zip("XYZ", spins):
                axis_row = QHBoxLayout()
                label = QLabel(axis)
                label.setBuddy(spin)
                spin.setAccessibleName(axis + " transform component")
                axis_row.addWidget(label)
                axis_row.addWidget(spin, 1)
                box.addLayout(axis_row)
            return row

        def set_enabled_for_selection(self, enabled: bool, reason: str = "") -> None:
            self.apply_button.setEnabled(enabled)
            for spin in self.translate + self.rotate + self.scale:
                spin.setEnabled(enabled)
            self.unsupported_note.setVisible(not enabled and bool(reason))
            self.unsupported_note.setText(reason)

        def show_prim(self, path: str, prim_type: str, editable: bool, reason: str = "") -> None:
            self.path_label.setText(path)
            self.type_label.setText(prim_type)
            self.set_enabled_for_selection(editable, reason)

    class MainWindow(QMainWindow):
        native_frame_ready = Signal(object)

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Untitled — LeRTX")
            self.resize(1440, 900)

            self.profile = copy.deepcopy(initial_profile)
            self.config_path = config_path
            self.current_scene_path = default_scene_path
            self.has_unsaved_changes = False
            self.requires_save_as = False
            self.worker = None
            self.connection_probe = transport_module.ConnectionProbe()
            from .photo import request_scene
            self.reconstruction_probe = transport_module.ConnectionProbe(request_scene)
            from .devices import scan_result
            self.device_probe = transport_module.ConnectionProbe(scan_result)
            self._hardware_windows = {}
            self.clock = SimulationClock(self.profile["physics"]["timestep_hz"])
            self._pending = []
            self._ready = False
            self._closing = False
            self._close_requested = False
            self._last_frame_at = time.monotonic()
            self._last_tick_started = self._last_frame_at
            self._next_frame_at = self._last_frame_at
            self._idle_frame = False
            self._image = None
            self._scene_units = 1.0
            self._open_requested = False
            self._photo_requested = False
            self._settings_requested = False

            self._build_toolbar()
            self._build_central_widget()
            self._build_docks()
            self._build_status_bar()
            from .robot_ui import build_robot_panel
            self.robot_panel = build_robot_panel(self)
            self.robot_dock = QDockWidget("Robot simulation", self)
            self.robot_dock.setObjectName("robotSimulation")
            from PySide6.QtWidgets import QScrollArea
            robot_scroll=QScrollArea();robot_scroll.setWidgetResizable(True);robot_scroll.setWidget(self.robot_panel)
            self.robot_dock.setWidget(robot_scroll)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.robot_dock)
            self.tabifyDockWidget(self.inspector_dock, self.robot_dock)
            self.robot_dock.raise_()

            self._frame_timer = QTimer(self)
            self._frame_timer.timeout.connect(self._on_tick)
            self._frame_timer.start(4)
            self.inspector.apply_button.clicked.connect(self._apply_transform)
            self._apply_theme()
            self._build_menus()
            from .desktop_state import read_state
            saved = read_state(self.config_path)
            from PySide6.QtCore import QByteArray
            for key,restore in [('geometry',self.restoreGeometry),('layout',self.restoreState)]:
                if isinstance(saved.get(key),str) and (key != 'layout' or saved.get('layout_version') == 2):
                    restore(QByteArray.fromBase64(saved[key].encode('ascii',errors='ignore')))

        def _build_menus(self):
            from PySide6.QtGui import QKeySequence
            menu=self.menuBar().addMenu('&File')
            actions={a.text():a for a in self.findChildren(QAction)}
            for title,key in [('Open USD',QKeySequence.StandardKey.Open),('Save',QKeySequence.StandardKey.Save),('Save As',QKeySequence.StandardKey.SaveAs)]:
                action=actions[title];action.setShortcut(key);menu.addAction(action)
            self.recent_menu=menu.addMenu('Open &Recent')
            self.recent_menu.aboutToShow.connect(self._update_recent)
            menu.addSeparator();quit_action=menu.addAction('Quit');quit_action.setShortcut(QKeySequence.StandardKey.Quit);quit_action.triggered.connect(self.close)
            view=self.menuBar().addMenu('&View')
            for dock in self.findChildren(QDockWidget):
                if not dock.objectName():dock.setObjectName(dock.windowTitle().replace(' ','').lower())
                view.addAction(dock.toggleViewAction())
            view.addAction(actions['Frame Selection'])
            help_menu=self.menuBar().addMenu('&Help')
            help_menu.addAction('Getting started',self._show_help)
            help_menu.addAction('Open application logs',self._open_logs)
            help_menu.addAction('About LeRTX',self._show_about)

        def _update_recent(self):
            from pathlib import Path
            from .desktop_state import read_state
            self.recent_menu.clear()
            paths=read_state(self.config_path).get('recent',[])
            if not isinstance(paths,list):paths=[]
            for path in paths[:10]:
                if not isinstance(path,str):continue
                action=self.recent_menu.addAction(Path(path).name.replace('&','&&'))
                action.setToolTip(path);action.setEnabled(Path(path).is_file())
                action.triggered.connect(lambda checked=False,p=path:self._open_recent(p))
            if not self.recent_menu.actions():self.recent_menu.addAction('No recent workspaces').setEnabled(False)

        def _open_recent(self,path):
            if self._pending:
                self.statusBar().showMessage('Wait for the current scene operation to finish');return
            self._after_discard_confirmation(lambda:self.open_scene(path))

        def _show_help(self):
            from .role_ui import role_html
            QMessageBox.information(self,'Getting started',role_html(
                'Your workspace contains an SO-101 leader and follower (see the color key under the viewport). Change their printed-part colors in device setup before connecting.\n\n'
                'Use Robot simulation to choose joint targets, then Play. The follower tracks the simulated leader. Pause holds the pose; Reset restores the workspace.\n\n'
                'Left- or right-drag an arm link in the viewport to move its joint directly, following the mouse. Alt-left-drag orbits the camera, middle-drag pans, and wheel or trackpad scroll zooms. Every leader and follower joint also has its own labeled slider in the Robot simulation panel — drag a slider or type a value there for the same live control without touching the viewport. Joint controls work while paused; uncheck Follower tracks the simulated leader to move the follower independently.\n\n'
                'To move anything else in the workspace — the ball, the obstacle, the work surface — left- or right-drag it in the viewport, same as an arm link. Selecting it also switches to the Inspector tab next to Robot simulation, where you can type exact Translate/Rotate/Scale values and click Apply transform. Use File → Save As to keep a workspace.\n\n'
                'These are simulated arms. No hardware port is opened. The leader trigger geometry and inertia are upstream estimates; contact hulls approximate individual mechanical parts.',self.profile))

        def _show_about(self):
            from .branding import VERSION
            QMessageBox.about(self,'About LeRTX',f'LeRTX {VERSION}\nA robot digital-twin workspace.\n\n'
                'Rendering: NVIDIA OVRTX / OVStage\nPhysics: Newton\nSO-101 models: TheRobotStudio, Apache-2.0\n\n'
                'Model licenses and provenance are included with the application.')

        def _open_logs(self):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            from .desktop_entry import log_directory
            path=log_directory();path.mkdir(parents=True,exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

        def _remember_document(self,path):
            from .desktop_state import remember_file
            try:remember_file(self.config_path,path)
            except OSError:self.statusBar().showMessage('Could not update recent workspaces')

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

            toolbar.addSeparator()

            devices_action = QAction("Devices", self)
            devices_action.triggered.connect(self._on_devices)
            toolbar.addAction(devices_action)
            setup_action = QAction('Set up real arms', self)
            setup_action.triggered.connect(self.open_setup)
            toolbar.addAction(setup_action)

            toolbar.addSeparator()

            photo_action = QAction("Reconstruct Photo", self)
            photo_action.triggered.connect(self._on_photo)
            toolbar.addAction(photo_action)

            toolbar.addSeparator()

            frame_action = QAction("Frame Selection", self)
            frame_action.triggered.connect(self._on_frame_selection)
            toolbar.addAction(frame_action)

            toolbar.addSeparator()

            settings_action = QAction("Settings", self)
            settings_action.triggered.connect(self._on_open_settings)
            toolbar.addAction(settings_action)

        def _build_central_widget(self) -> None:
            central = QWidget()
            layout = QVBoxLayout(central)
            self.reconstruction_warning = QLabel("Unverified photo draft — dimensions are estimates; not safe for motion planning.")
            self.reconstruction_warning.setWordWrap(True)
            self.reconstruction_warning.setStyleSheet("color: #ffd083; padding: 8px;")
            self.reconstruction_warning.hide()
            layout.addWidget(self.reconstruction_warning)

            self.loading_row = QWidget()
            loading_layout = QHBoxLayout(self.loading_row)
            loading_layout.setContentsMargins(0, 0, 0, 4)
            self.loading_bar = QProgressBar()
            self.loading_bar.setRange(0, 0)  # indeterminate: pulses while the duration is unknown
            self.loading_bar.setTextVisible(False)
            self.loading_bar.setFixedHeight(6)
            self.loading_label = QLabel("Loading workspace…")
            loading_layout.addWidget(self.loading_bar, 1)
            loading_layout.addWidget(self.loading_label)
            self.loading_row.hide()
            layout.addWidget(self.loading_row)

            from .viewport_ui import build_viewport
            self.viewport_label = build_viewport(self)
            self.viewport_label.setObjectName("viewport")
            self.viewport_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.viewport_label.setMinimumSize(320, 180)
            self.viewport_label.setText("Loading workspace…")
            self.viewport_label.setToolTip('Left- or right-drag an arm link to move its joint, or any other object (ball, obstacle, surface) to move it directly — both follow the mouse. Alt-left-drag: orbit · Middle-drag: pan · Scroll: zoom. Every joint also has a labeled slider in Robot simulation; any object\'s exact position is in the Inspector tab.')
            layout.addWidget(self.viewport_label, stretch=1)

            legend_row = QHBoxLayout()
            legend_row.setContentsMargins(0, 0, 0, 0)
            self.arm_swatches = {}
            from .arm_colors import role_color
            for role, name in (("leader", "Leader"), ("follower", "Follower")):
                swatch_color = role_color(self.profile, role)
                swatch = QLabel()
                self.arm_swatches[role] = swatch
                swatch.setFixedSize(16, 16)
                swatch.setPixmap(dot(swatch_color))
                legend_row.addWidget(swatch)
                from PySide6.QtWidgets import QLabel as PlainLabel
                legend_row.addWidget(PlainLabel(name))
            legend_row.addStretch(1)
            layout.addLayout(legend_row)

            hint = QLabel('Left- or right-drag a link: move its joint · Drag any other object: move it directly · Alt-left-drag: orbit · Middle-drag: pan · Scroll: zoom')
            hint.setWordWrap(True)
            layout.addWidget(hint)

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
            hierarchy_widget.setMinimumWidth(200)
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
            self.inspector_dock = inspector_dock
            self.inspector = InspectorPanel()
            self.inspector.setMinimumWidth(300)
            self.inspector.setMaximumWidth(420)
            inspector_dock.setWidget(self.inspector)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, inspector_dock)
            self.resizeDocks([hierarchy_dock, inspector_dock], [240, 360], Qt.Orientation.Horizontal)

        def _build_status_bar(self) -> None:
            from .role_ui import status_bar
            self.setStatusBar(status_bar(lambda:self.profile))

        def _on_search_changed(self, text: str) -> None:
            lowered = text.lower()
            from PySide6.QtWidgets import QTreeWidgetItemIterator
            iterator = QTreeWidgetItemIterator(self.tree)
            items = []
            while iterator.value():
                items.append(iterator.value())
                iterator += 1
            if lowered and getattr(self, "_search_expanded", None) is None:
                self._search_expanded = {item.data(0, Qt.ItemDataRole.UserRole)
                                         for item in items if item.isExpanded()}
            visible = set()
            for item in items:
                path = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
                if not lowered or lowered in path.lower():
                    ancestor = item
                    while ancestor is not None:
                        visible.add(id(ancestor))
                        ancestor = ancestor.parent()
            for item in items:
                item.setHidden(id(item) not in visible)
                if lowered and id(item) in visible and item.childCount():
                    item.setExpanded(True)
                elif not lowered and getattr(self, "_search_expanded", None) is not None:
                    item.setExpanded(item.data(0, Qt.ItemDataRole.UserRole) in self._search_expanded)
            if not lowered:
                self._search_expanded = None
            if self.tree.currentItem() is not None and self.tree.currentItem().isHidden():
                self.tree.clearSelection()

        def _rebuild_hierarchy(self, hierarchy):
            selected_path = self._selected_path()
            previous = getattr(self, "_tree_items", {})
            expanded = {path for path, item in previous.items() if item.isExpanded()}
            self.tree.blockSignals(True)
            try:
                self.tree.clear()
                self._tree_items = {}
                for prim in sorted(hierarchy, key=lambda prim: (prim["path"].count("/"), prim["path"])):
                    path = prim["path"]
                    item = QTreeWidgetItem([path.rsplit("/", 1)[-1] or path])
                    from .role_ui import role_icon
                    item.setIcon(0,role_icon(item.text(0),self.profile))
                    item.setData(0, Qt.ItemDataRole.UserRole, path)
                    item.setToolTip(0, path)
                    parent = self._tree_items.get(path.rsplit("/", 1)[0])
                    if parent is not None:
                        parent.addChild(item)
                    else:
                        self.tree.addTopLevelItem(item)
                    self._tree_items[path] = item
                    item.setExpanded(path in expanded or (not previous and parent is None))
                if selected_path in self._tree_items:
                    self.tree.setCurrentItem(self._tree_items[selected_path])
            finally:
                self.tree.blockSignals(False)
            self._on_search_changed(self.search_edit.text())

        def _command(self, fn, callback=None, *, rendering=False):
            if not rendering:
                if self._idle_frame:
                    self._last_tick_started = time.monotonic()
                self._idle_frame = False
                self._next_frame_at = time.monotonic()
                self._frame_timer.setInterval(4)
            if self.worker is None or self._closing:
                return
            self._pending.append((self.worker.submit(fn), callback))

        def _selected_path(self):
            items = self.tree.selectedItems()
            return items[0].data(0, Qt.ItemDataRole.UserRole) if items else None

        def _on_selection_changed(self):
            path = self._selected_path()
            if self._ready and self.worker and hasattr(self.worker, 'select'):
                def selected_joint(value):
                    if path==self._selected_path() and value.get('joint'):
                        self.robot_dock.show();self.robot_dock.raise_()
                self._command(lambda: self.worker.select(path),selected_joint)
            self.inspector.set_enabled_for_selection(False)
            if path is None:
                self.inspector.show_prim("", "", False)
                return
            def selected(value):
                if path != self._selected_path():
                    return
                if "error" in value:
                    self.inspector.show_prim(path, self._prim_types.get(path, ""), False, value["error"])
                    return
                self.inspector.show_prim(path, self._prim_types.get(path, ""), True)
                self.inspector_dock.show();self.inspector_dock.raise_()
                for spins, name in ((self.inspector.translate, "translation"),
                                    (self.inspector.rotate, "rotation"), (self.inspector.scale, "scale")):
                    for spin, component in zip(spins, value[name]):
                        spin.setValue(component * self._display_factor() if name == "translation" else component)
            def inspect():
                try:
                    return self.worker.inspect(path)
                except ValueError as exc:
                    return {"error": str(exc)}
            self._command(inspect, selected)

        def _apply_transform(self):
            path = self._selected_path()
            if not path or not self._ready:
                return
            values = [[spin.value() for spin in spins] for spins in
                      (self.inspector.translate, self.inspector.rotate, self.inspector.scale)]
            values[0] = [value / self._display_factor() for value in values[0]]
            self._ready = False
            self._command(lambda: self.worker.edit(path, *values), self._apply_status)

        def _set_loading(self, active, message="Loading workspace…"):
            self.loading_label.setText(message)
            self.loading_row.setVisible(active)

        def _apply_status(self, status):
            self._set_loading(False)
            self.statusBar().clearMessage()
            self.robot_panel.update_state(status.get("robots"))
            self.reconstruction_warning.setVisible(status.get("reconstruction_status") == "unverified")
            self._diagnostics = status.get("diagnostics", {})
            self._scene_units = status.get("meters_per_unit", 1.0)
            self.inspector.translate_label.setText(f'Translate ({self.profile["general"]["display_units"]})')
            self.current_scene_path = status["path"]
            self.has_unsaved_changes = status["dirty"]
            from pathlib import Path
            name = "Untitled" if self.requires_save_as else Path(self.current_scene_path).name
            self.setWindowTitle(name + (" •" if self.has_unsaved_changes else "") + " — LeRTX")
            self.clock.playing = status["playing"]
            self.clock.sim_time = status["time"]
            self.play_button.setText("Pause" if status["playing"] else "Play")
            self.play_button.setEnabled(not status["physics_error"])
            self._simulation_available=not status['physics_error']
            if status.get('robots',{}).get('live_roles'):self.play_button.setEnabled(False)
            self.native_status_label.setText(status["physics_error"] or "Native: ready")
            self._ready = True
            hierarchy = status["hierarchy"]
            if hierarchy != getattr(self, "_hierarchy", None):
                self._hierarchy = hierarchy
                self._prim_types = {p["path"]: p["type"] for p in hierarchy}
                self._rebuild_hierarchy(hierarchy)
            self._on_selection_changed()

        def _after_discard_confirmation(self, action):
            if not self.has_unsaved_changes:
                action()
                return
            choice = QMessageBox.question(self, "Unsaved changes",
                "Save changes before continuing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if choice == QMessageBox.StandardButton.Discard:
                action()
            elif choice == QMessageBox.StandardButton.Save:
                def saved(status):
                    self._apply_status(status)
                    action()
                self._save_document(saved)

        def _on_open(self):
            if self._pending:
                self._open_requested = True
                return
            path, _ = QFileDialog.getOpenFileName(self, "Open USD", "", "USD (*.usd *.usda *.usdc)")
            if path:
                self._after_discard_confirmation(lambda: self.open_scene(path))

        def _on_photo(self):
            if self._pending:
                self._photo_requested = True
                return
            if not self._ready:
                self.statusBar().showMessage("Open a ready workspace before reconstructing a photo")
                return
            from .photo_ui import build_photo_dialog
            dialog = build_photo_dialog(self.profile, self.reconstruction_probe, self)
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            result = dialog.result_scene
            dialog.deleteLater()
            if not accepted or result is None:
                return
            def adopt():
                self._ready = False
                self.native_status_label.setText("Native: loading photo draft")
                self._set_loading(True, "Loading photo draft…")
                def adopted(status):
                    self.requires_save_as = True
                    self._apply_status(status)
                self._command(lambda: self.worker.import_photo_draft(result["scene_text"],
                    result["image_sha256"], result["model"], result.get("focus_id")), adopted)
            self._after_discard_confirmation(adopt)

        def open_scene(self, path):
            from pathlib import Path
            self.viewport_label.cancel()
            for panel in self._hardware_windows.values():panel.live.setChecked(False)
            if self.worker is None:
                try:
                    self.worker = worker_factory()
                    self.worker.start()
                except Exception as exc:
                    self._show_error(exc)
                    return
            self._ready = False
            self.native_status_label.setText("Native: loading")
            self._set_loading(True, f"Loading {Path(path).name}…")
            previous_path = self.current_scene_path
            def opened(status):
                from pathlib import Path
                if Path(status["path"]).resolve() != Path(previous_path).resolve():
                    self.requires_save_as = False
                self._apply_status(status)
                if not self.requires_save_as:self._remember_document(status["path"])
            self._command(lambda: self.worker.open_document(path), opened)

        def _on_save(self):
            self._save_document(self._apply_status)

        def _save_document(self, callback, force_as=False):
            path = None
            if force_as or self.requires_save_as:
                path, _ = QFileDialog.getSaveFileName(self, "Save USD As", "", "USD (*.usd *.usda *.usdc)")
                if not path:
                    return
                if self.requires_save_as:
                    from pathlib import Path
                    if Path(path).resolve().is_relative_to(Path(self.current_scene_path).resolve().parent):
                        self._show_error(ValueError("Choose a location outside the temporary workspace"))
                        return
            def saved(status):
                self.requires_save_as = False
                self._remember_document(status["path"])
                callback(status)
            self._command(lambda: self.worker.save(path), saved)

        def _on_save_as(self):
            self._save_document(self._apply_status, force_as=True)

        def _on_open_settings(self):
            if self._pending:
                self._settings_requested = True
                return
            dialog = self.create_settings_dialog()
            try:
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                profile = dialog.result_profile()
            finally:
                dialog.deleteLater()
            if profile is None:
                return
            from .arm_colors import role_color
            if any(role_color(profile,r)!=role_color(self.profile,r) for r in ('leader','follower')) and any(
                    p.session and p.session._thread.is_alive() for p in self._hardware_windows.values()):
                self._show_error(ValueError('Close hardware sessions before changing arm colors.'))
                return
            restart = profile["rendering"] != self.profile["rendering"]
            if restart and QMessageBox.question(self, "Restart renderer",
                    "Apply rendering settings and restart the renderer?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            def configured(status):
                self.profile = copy.deepcopy(profile)
                self.refresh_arm_colors()
                self._apply_theme()
                self._apply_status(status)
            if self.worker:
                self.viewport_label.cancel()
                self._ready = False
                self.native_status_label.setText("Native: applying settings")
                self._set_loading(True, "Applying settings…")
                self._command(lambda: self.worker.configure(profile, self.config_path), configured)
            else:
                try:
                    config_module.save_profile(profile, self.config_path)
                except Exception as exc:
                    self._show_error(exc)
                    return
                self.profile = copy.deepcopy(profile)
                self.refresh_arm_colors()
                self._apply_theme()
                self.statusBar().clearMessage()

        def create_settings_dialog(self):
            return SettingsDialog(self.profile, self)

        def refresh_arm_colors(self):
            from .arm_colors import role_color
            role_profile[0]=self.profile
            for role, swatch in self.arm_swatches.items():
                swatch.setPixmap(dot(role_color(self.profile, role)))
            from PySide6.QtWidgets import QWidget
            for child in self.findChildren(QWidget):
                refresh=getattr(child,'refresh_role_colors',None)
                if refresh:refresh()
            from .role_ui import role_icon
            for item in getattr(self,'_tree_items',{}).values():
                item.setIcon(0,role_icon(item.text(0),self.profile))
            wizard=getattr(self,'_setup_window',None)
            if wizard and not wizard.closing:wizard.sync_identity()

        def _on_devices(self):
            from pathlib import Path
            from .devices_ui import build_devices_dialog
            dialog = build_devices_dialog(self.profile, self.device_probe,
                Path(self.config_path).parent / "devices.json", self)
            dialog.exec()
            dialog.deleteLater()

        def open_hardware(self,candidate,role):
            panel=self._hardware_windows.get(role)
            if panel and panel.session._thread.is_alive():
                panel.show();panel.raise_();panel.activateWindow();return
            from .hardware_ui import build_hardware_panel
            panel=build_hardware_panel(self,candidate,role)
            self._hardware_windows[role]=panel
            panel.show()

        def open_setup(self):
            previous=getattr(self,'_setup_window',None)
            if previous and previous.isVisible():
                previous.raise_();previous.activateWindow();return
            from .setup_ui import build_setup_wizard
            self._setup_window=build_setup_wizard(self)
            self._setup_window.show()

        def _display_factor(self):
            unit = self.profile["general"]["display_units"]
            return self._scene_units / {"m": 1., "cm": .01, "mm": .001}[unit]

        def _apply_theme(self):
            if self.profile["general"]["theme"] == "dark":
                self.setStyleSheet(CHARCOAL_STYLESHEET)
            else:
                self.setStyleSheet("""
                    QWidget { background: #f1f4f5; color: #182428; font-size: 13px; }
                    QLineEdit, QTreeWidget, QSpinBox, QDoubleSpinBox { background: white; color: #182428; padding: 4px; }
                    QPushButton { background: #dce8e8; color: #182428; padding: 6px 12px; }
                    QTreeWidget::item:selected { background: #267c78; color: white; }
                    QLabel#viewport { background: #101214; }
                """)

        def _camera(self, **kwargs):
            if self._ready and not self._pending:
                self._command(lambda: self.worker.move_camera(**kwargs))

        def _on_frame_selection(self):
            path = self._selected_path()
            if self._ready:
                self._command(lambda: self.worker.frame_selection(path))

        def _on_play_pause(self):
            enabled = not self.clock.playing
            if self._ready:
                self._command(lambda: self.worker.set_playing(enabled), self._apply_status)

        def _on_reset(self):
            self.viewport_label.cancel()
            if self._ready:
                self._ready = False
                self._command(self.worker.reset, self._apply_status)

        def _show_error(self, exc):
            self.viewport_label.cancel()
            self._set_loading(False)
            self.native_status_label.setText(f"Native: {exc}")
            self.statusBar().showMessage(str(exc))
            if self.worker and self.worker._stop_event.is_set():
                self._ready = False
            elif self.worker and getattr(self, "_hierarchy", None) is not None:
                self._ready = True

        def _display_image(self):
            if self._image is not None:
                self.viewport_label.setPixmap(QPixmap.fromImage(self._image).scaled(
                    self.viewport_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))

        def _accept_frame(self, result):
            if result.get("unchanged"):
                self._idle_frame = True
                self._frame_timer.setInterval(50)
                self.frame_rate_label.setText("Paused")
                return
            frame = result["frame"]
            if frame.dtype_name != "uint8" or frame.channels not in (3, 4):
                raise ValueError("Unsupported native display frame format")
            fmt = QImage.Format.Format_RGBA8888 if frame.channels == 4 else QImage.Format.Format_RGB888
            self._image = QImage(frame.data, frame.width, frame.height,
                                 frame.width*frame.channels, fmt).copy()
            self._display_image()
            self.native_frame_ready.emit(self._image)
            self.robot_panel.update_state(result.get("robots"))
            self.play_button.setEnabled(getattr(self,'_simulation_available',True) and not result.get('robots',{}).get('live_roles'))
            if result.get('joint_target'):
                self.robot_panel.show_target(*result['joint_target'])
            self.clock.sim_time = result["time"]
            self.clock.playing = result["playing"]
            self.play_button.setText("Pause" if result["playing"] else "Play")
            self.sim_time_label.setText(f't={result["time"]:.2f}s')
            now = time.monotonic()
            self.frame_rate_label.setText(f"{1/max(now-self._last_frame_at, 0.001):.1f} fps")
            self._last_frame_at = now

        def _on_tick(self):
            pending, self._pending = self._pending, []
            for future, callback in pending:
                if not future.done():
                    self._pending.append((future, callback))
                    continue
                try:
                    value = future.result()
                    if callback:
                        callback(value)
                except Exception as exc:
                    self._show_error(exc)
            if self._closing:
                if any(p.session._thread.is_alive() or (p.closing and not p.shutdown_complete) for p in self._hardware_windows.values()):
                    return
                if self.worker is None or self.worker._thread is None or not self.worker._thread.is_alive():
                    if self.worker:
                        self.worker.stop()
                        self.worker = None
                    self.close()
                return
            if self._close_requested and not self._pending:
                self._close_requested = False
                self.close()
                return
            if self._open_requested and not self._pending:
                self._open_requested = False
                self._on_open()
                return
            if self._photo_requested and not self._pending:
                self._photo_requested = False
                self._on_photo()
                return
            if self._settings_requested and not self._pending:
                self._settings_requested = False
                self._on_open_settings()
                return
            now = time.monotonic()
            self.robot_panel.flush()
            self.viewport_label.flush()
            if self._ready and not self._idle_frame and not self._pending and now >= self._next_frame_at:
                # Schedule start-to-start. Waiting a frame interval after the
                # previous completion added rendering time to every deadline
                # and passed only that idle interval to the simulation clock.
                elapsed = now-self._last_tick_started
                self._last_tick_started = now
                self._next_frame_at = max(now, self._next_frame_at + 1/self.profile["rendering"]["target_fps"])
                self._command(lambda: self.worker.tick(elapsed), self._accept_frame, rendering=True)

        def closeEvent(self, event):
            self.viewport_label.cancel()
            for panel in self._hardware_windows.values():
                if panel.session and panel.session._thread.is_alive():panel.shutdown()
            if self._closing and self.worker is None:
                self._frame_timer.stop()
                from .desktop_state import save_state
                try:save_state(self.config_path,{"layout_version":2,"geometry":bytes(self.saveGeometry().toBase64()).decode(),"layout":bytes(self.saveState().toBase64()).decode()})
                except OSError:pass
                event.accept()
                return
            event.ignore()
            if self._pending:
                self._close_requested = True
                self.statusBar().showMessage("Finishing current operation before closing")
                return
            def begin_close():
                self._closing = True
                self._ready = False
                if self.worker:
                    self.worker._stop_event.set()
            self._after_discard_confirmation(begin_close)

    return MainWindow()
