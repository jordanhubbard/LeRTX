"""Controls for the real simulated articulations, separate from USB devices."""
from __future__ import annotations

import math


def build_robot_panel(window):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QComboBox, QSlider
    from .robot import JOINT_NAMES, joint_limits, home_positions

    class RobotPanel(QWidget):
        def __init__(self):
            super().__init__(window)
            self.state={};self.selected=None
            self.setMinimumWidth(370)
            self.setMaximumWidth(480)
            layout=QVBoxLayout(self)
            note=QLabel('SO-101 · Simulated leader and follower\nPlay to track targets; viewport drags also preview motion while paused.')
            note.setWordWrap(True);layout.addWidget(note)
            self.follow=QCheckBox('Follower tracks the simulated leader')
            self.follow.setChecked(True);layout.addWidget(self.follow)
            self.role=QComboBox();self.role.addItems(['leader','follower']);layout.addWidget(self.role)
            grid=QGridLayout();layout.addLayout(grid)
            for column,title in enumerate(['Joint','Target','Leader','Follower']):grid.addWidget(QLabel(title),0,column)
            self.inputs={};self.readings={}
            for row,name in enumerate(JOINT_NAMES,1):
                grid.addWidget(QLabel(name.replace('_',' ').title()),row,0)
                spin=QDoubleSpinBox();spin.setDecimals(1);spin.setSingleStep(5);spin.setKeyboardTracking(False);spin.setMaximumWidth(100)
                self.inputs[name]=spin;grid.addWidget(spin,row,1)
                for column,role in enumerate(('leader','follower'),2):
                    label=QLabel('—');self.readings[role,name]=label;grid.addWidget(label,row,column)
            self.apply=QPushButton('Apply joint targets');layout.addWidget(self.apply)
            self.selection_label=QLabel('Select an arm link to turn its joint here.');self.selection_label.setWordWrap(True);layout.addWidget(self.selection_label)
            self.joint_slider=QSlider(Qt.Orientation.Horizontal);self.joint_slider.setRange(0,1000);self.joint_slider.setEnabled(False)
            self.joint_slider.setAccessibleName('Selected joint angle');layout.addWidget(self.joint_slider)
            self.joint_slider.valueChanged.connect(self.slide_joint)
            self.status=QLabel('Waiting for robot workspace…');self.status.setWordWrap(True);layout.addWidget(self.status);layout.addStretch(1)
            self.role.currentTextChanged.connect(self.load_role)
            self.follow.toggled.connect(self.set_following)
            self.apply.clicked.connect(self.command)
            self.load_role('leader');self.setEnabled(False)

        def load_role(self,role):
            for name,spin in self.inputs.items():
                low,high=joint_limits(role)[name]
                spin.setRange(0,100) if name=='gripper' else spin.setRange(math.degrees(low),math.degrees(high))
                spin.setSuffix(' %' if name=='gripper' else '°')
                q=home_positions(role)[name]
                spin.setValue((q-low)/(high-low)*100 if name=='gripper' else math.degrees(q))
            self.apply.setEnabled(not self.state.get('live_roles') and (role=='leader' or not self.follow.isChecked()))

        def set_following(self,value):
            self.apply.setEnabled(self.role.currentText()=='leader' or not value)
            if window._ready and not window._pending:
                window._command(lambda:window.worker.command_robot('leader',following=value),window._apply_status)

        def command(self):
            if not window._ready or window._pending:
                self.status.setText('Wait for the current scene operation to finish.');return
            role=self.role.currentText();positions={}
            for name,spin in self.inputs.items():
                low,high=joint_limits(role)[name]
                positions[name]=low+(high-low)*spin.value()/100 if name=='gripper' else max(low,min(high,math.radians(spin.value())))
            window._command(lambda:window.worker.command_robot(role,positions),window._apply_status)

        def update_state(self,state):
            self.state=state or {}
            available=bool(state and state.get('positions'))
            self.setEnabled(available)
            if not available:
                self.status.setText('Open a workspace containing SO-101 articulations.');return
            self.follow.blockSignals(True);self.follow.setChecked(state['following']);self.follow.blockSignals(False)
            live=state.get('live_roles',[])
            self.follow.setEnabled(not live)
            self.apply.setEnabled(not live and (self.role.currentText()=='leader' or not state['following']))
            if self.selected:
                was_locked=self.selected['locked']
                self.selected['locked']=bool(live) or (self.selected['role']=='follower' and state['following'])
                self.selected['lock_reason']='Disable physical live view before simulated manipulation.' if live else 'Disable following to manipulate the follower.'
                self.joint_slider.setEnabled(not self.selected['locked'])
                if was_locked!=self.selected['locked']:self.select_joint({'joint':self.selected})
            for role,values in state['positions'].items():
                for name,value in values.items():
                    low,high=joint_limits(role)[name]
                    number=(value-low)/(high-low)*100 if name=='gripper' else math.degrees(value)
                    self.readings[role,name].setText(f'{number:.1f}'+(' %' if name=='gripper' else '°'))
            self.status.setText('Physical live view: '+', '.join(live)+' · simulation paused' if live else 'Simulated positions · hardware controls are separate')

        def select_joint(self,result):
            self.selected=result.get('joint')
            joint=self.selected
            self.joint_slider.setEnabled(bool(joint and not joint['locked']))
            if not joint:
                self.selection_label.setText('Select an arm link to turn its joint here.');return
            self.role.setCurrentText(joint['role'])
            self.selection_label.setText(joint['role'].title()+' · '+joint['name'].replace('_',' ')+
                (' — '+joint.get('lock_reason','Disable following to manipulate.') if joint['locked'] else ' — drag this slider or the arm link'))
            self.joint_slider.blockSignals(True)
            self.joint_slider.setValue(round(1000*(joint['value']-joint['low'])/(joint['high']-joint['low'])))
            self.joint_slider.blockSignals(False)

        def slide_joint(self,value):
            joint=self.selected
            if joint and not joint['locked'] and window._ready:
                radians=joint['low']+(joint['high']-joint['low'])*value/1000
                window.viewport_label.intent=(joint['role'],joint['name'],radians)
                self.selection_label.setText(joint['role'].title()+' · '+joint['name'].replace('_',' ')+f': {math.degrees(radians):.1f}° target')

        def show_target(self, role, name, value):
            self.role.setCurrentText(role)
            low, high = joint_limits(role)[name]
            self.inputs[name].setValue((value-low)/(high-low)*100 if name=='gripper' else math.degrees(value))

    return RobotPanel()
