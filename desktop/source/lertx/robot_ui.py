"""Always-visible controls for the simulated articulations, separate from USB devices."""
from __future__ import annotations

import math


def build_robot_panel(window):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QSlider
    from .robot import JOINT_NAMES, joint_limits

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

        def _locked(self,role,name):
            live=self.state.get('live_roles') or []
            return bool(live) or (role=='follower' and self.state.get('following'))

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
                for name,value in values.items():
                    locked=self._locked(role,name)
                    slider=self.sliders[role,name];spin=self.values[role,name]
                    slider.setEnabled(not locked);spin.setEnabled(not locked)
                    if slider.isSliderDown() or spin.hasFocus():
                        continue
                    self._set_display(role,name,value)
            self.status.setText('CALIBRATION PREVIEW · not verified physical coordinates' if state.get('setup_roles') else
                ('Physical live view: '+', '.join(live)+' · simulation paused' if live else 'Simulation only · no USB motor commands are sent from these controls'))

        def show_target(self,role,name,value):
            self._set_display(role,name,value)

    return RobotPanel()
