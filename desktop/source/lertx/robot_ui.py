"""Always-visible controls for the simulated articulations, separate from USB devices."""
from __future__ import annotations

import math


def build_robot_panel(window):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QDoubleSpinBox,
        QCheckBox, QPushButton, QSlider, QComboBox, QInputDialog)
    from .robot import JOINT_NAMES, joint_limits

    from .role_ui import widgets
    QLabel,QPushButton,QCheckBox=widgets(lambda: window.profile)

    class RobotPanel(QWidget):
        def __init__(self):
            super().__init__(window)
            self.state={};self.pending_follow=None
            self.setMinimumWidth(420)
            self.setMaximumWidth(560)
            layout=QVBoxLayout(self)
            note=QLabel('Drag any slider below (or type a value) to move that joint directly. Motion works '
                'while paused. You can also right-click or left-drag an arm link in the viewport — both grab '
                "and drive the joint the same way. Alt-left-drag orbits the camera; middle-drag pans; wheel "
                'or trackpad scroll zooms.')
            note.setWordWrap(True);layout.addWidget(note)

            layout.addWidget(QLabel('<b>Saved poses</b>'))
            preset_row=QHBoxLayout()
            self.preset_combo=QComboBox();preset_row.addWidget(self.preset_combo,1)
            self.load_button=QPushButton('Load');self.load_button.clicked.connect(self.load_preset)
            preset_row.addWidget(self.load_button)
            self.save_button=QPushButton('Save current as…');self.save_button.clicked.connect(self.save_preset)
            preset_row.addWidget(self.save_button)
            layout.addLayout(preset_row)
            self.refresh_presets()

            setup=QPushButton('Set up and calibrate real USB arms…');setup.clicked.connect(window.open_setup);layout.addWidget(setup)
            self.follow=QCheckBox('Follower tracks the simulated leader')
            self.follow.setChecked(True);layout.addWidget(self.follow)

            grid=QGridLayout()
            grid.addWidget(QLabel('Joint'),0,0)
            grid.addWidget(QLabel('Leader'),0,1,1,2)
            grid.addWidget(QLabel('Follower'),0,3,1,2)
            self._range={}
            self.sliders={}
            self.values={}
            for row,name in enumerate(JOINT_NAMES,1):
                grid.addWidget(QLabel(name.replace('_',' ').title()),row,0)
                for column,role in ((1,'leader'),(3,'follower')):
                    low,high=joint_limits(role)[name]
                    self._range[role,name]=(low,high)
                    gripper=name=='gripper'
                    slider=QSlider(Qt.Orientation.Horizontal)
                    slider.setRange(0,1000)
                    slider.setAccessibleName(f"{role.title()} {name.replace('_',' ')} target")
                    value=QDoubleSpinBox()
                    value.setDecimals(1);value.setKeyboardTracking(False);value.setMaximumWidth(80)
                    value.setRange(0,100) if gripper else value.setRange(math.degrees(low),math.degrees(high))
                    value.setSuffix(' %' if gripper else '°')
                    value.setAccessibleName(f"{role.title()} {name.replace('_',' ')} target value")
                    grid.addWidget(slider,row,column)
                    grid.addWidget(value,row,column+1)
                    self.sliders[role,name]=slider
                    self.values[role,name]=value
                    slider.valueChanged.connect(lambda v,r=role,n=name:self._slide(r,n,v))
                    value.valueChanged.connect(lambda v,r=role,n=name:self._enter_value(r,n,v))
            layout.addLayout(grid)

            self.status=QLabel('Waiting for robot workspace…');self.status.setWordWrap(True);layout.addWidget(self.status)
            layout.addStretch(1)
            self.follow.toggled.connect(self.set_following)
            self.setEnabled(False)

        def set_following(self,value):
            self.pending_follow=value
            self.flush()

        def flush(self):
            if self.pending_follow is not None and window._ready and not window._pending:
                value,self.pending_follow=self.pending_follow,None
                window._command(lambda:window.worker.command_robot('leader',following=value),window._apply_status)

        def refresh_presets(self):
            from .robot_poses import list_presets
            self.preset_combo.clear()
            presets=list_presets(window.config_path)
            for label,path,builtin in presets:
                self.preset_combo.addItem(label if builtin else label+' (custom)',str(path))
            if not presets:
                self.preset_combo.addItem('No saved poses yet',None)

        def load_preset(self):
            path=self.preset_combo.currentData()
            if path is None:
                self.status.setText('No pose selected to load.');return
            if not window._ready or window._pending:
                self.status.setText('Wait for the current scene operation to finish, then try Load again.');return
            from .robot_poses import load_pose
            try:
                fractions=load_pose(path)
            except (OSError,ValueError) as exc:
                self.status.setText(f'Could not load pose: {exc}');return
            positions={role:{name:self._range[role,name][0]+(self._range[role,name][1]-self._range[role,name][0])*value
                for name,value in fractions[role].items()} for role in ('leader','follower')}
            label=self.preset_combo.currentText()
            self.status.setText(f'Loading pose "{label}"…')
            def follower_done(status):
                window._apply_status(status)
            def leader_done(status):
                window._apply_status(status)
                window._command(lambda:window.worker.command_robot('follower',positions['follower']),follower_done)
            window._command(lambda:window.worker.command_robot('leader',positions['leader'],following=False),leader_done)

        def save_preset(self):
            positions=self.state.get('positions') or {}
            if 'leader' not in positions or 'follower' not in positions:
                self.status.setText('Open a workspace with both arms before saving a pose.');return
            name,ok=QInputDialog.getText(self,'Save pose','Pose name:')
            if not ok or not name.strip():
                return
            fractions={role:{name_:(positions[role][name_]-self._range[role,name_][0])/
                (self._range[role,name_][1]-self._range[role,name_][0]) for name_ in JOINT_NAMES}
                for role in ('leader','follower')}
            from .robot_poses import save_pose
            try:
                save_pose(window.config_path,name,fractions)
            except (OSError,ValueError) as exc:
                self.status.setText(f'Could not save pose: {exc}');return
            self.refresh_presets()
            self.status.setText(f'Saved pose "{name.strip()}".')

        def _locked(self,role,name):
            live=self.state.get('live_roles') or []
            return bool(live) or (role=='follower' and self.state.get('following'))

        def _lock_reason(self,role):
            live=self.state.get('live_roles') or []
            if live:
                return 'Disable physical live view before simulated manipulation.'
            if role=='follower' and self.state.get('following'):
                return 'Uncheck "Follower tracks the simulated leader" above to move the follower directly.'
            return ''

        def _slide(self,role,name,slider_value):
            if not self.sliders[role,name].isEnabled() or not window._ready:
                return
            low,high=self._range[role,name]
            radians=low+(high-low)*slider_value/1000
            window.viewport_label.intent=(role,name,radians)
            spin=self.values[role,name]
            spin.blockSignals(True)
            spin.setValue(100*slider_value/1000 if name=='gripper' else math.degrees(radians))
            spin.blockSignals(False)
            self.status.setText(f"{role.title()} · {name.replace('_',' ')}: {math.degrees(radians):.1f}° target")

        def _enter_value(self,role,name,value):
            if not self.values[role,name].isEnabled() or not window._ready:
                return
            low,high=self._range[role,name]
            radians=(low+(high-low)*value/100) if name=='gripper' else math.radians(value)
            radians=max(low,min(high,radians))
            window.viewport_label.intent=(role,name,radians)
            self._set_slider(role,name,radians)
            self.status.setText(f"{role.title()} · {name.replace('_',' ')}: {math.degrees(radians):.1f}° target")

        def _set_slider(self,role,name,radians):
            low,high=self._range[role,name]
            slider=self.sliders[role,name]
            slider.blockSignals(True)
            slider.setValue(round(1000*(radians-low)/(high-low)))
            slider.blockSignals(False)

        def _set_display(self,role,name,radians):
            low,high=self._range[role,name]
            fraction=(radians-low)/(high-low)
            slider=self.sliders[role,name];spin=self.values[role,name]
            slider.blockSignals(True);spin.blockSignals(True)
            slider.setValue(round(1000*fraction))
            spin.setValue(100*fraction if name=='gripper' else math.degrees(radians))
            slider.blockSignals(False);spin.blockSignals(False)

        def update_state(self,state):
            self.state=state or {}
            available=bool(state and state.get('positions'))
            self.setEnabled(available)
            if not available:
                self.status.setText('Open a workspace containing SO-101 articulations.');return
            self.follow.blockSignals(True);self.follow.setChecked(state['following'] if self.pending_follow is None else self.pending_follow);self.follow.blockSignals(False)
            live=state.get('live_roles',[])
            self.follow.setEnabled(not live)
            for role,values in state['positions'].items():
                reason=self._lock_reason(role)
                for name,value in values.items():
                    locked=self._locked(role,name)
                    slider=self.sliders[role,name];spin=self.values[role,name]
                    slider.setEnabled(not locked);spin.setEnabled(not locked)
                    slider.setToolTip(reason if locked else '');spin.setToolTip(reason if locked else '')
                    if slider.isSliderDown() or spin.hasFocus():
                        continue
                    self._set_display(role,name,value)
            self.status.setText('CALIBRATION PREVIEW · not verified physical coordinates' if state.get('setup_roles') else
                ('Physical live view: '+', '.join(live)+' · simulation paused' if live else 'Simulation only · no USB motor commands are sent from these controls'))

        def show_target(self,role,name,value):
            self._set_display(role,name,value)

    return RobotPanel()
