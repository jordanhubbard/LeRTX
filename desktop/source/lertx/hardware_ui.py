"""Explicit hardware connection, telemetry, arming and held manual motion."""
import math
import time
from .robot import JOINT_NAMES
from .hardware import HardwareSession
from .hardware_calibration import Calibration, load_binding, binding_targets


def build_hardware_panel(owner,candidate,role,session_factory=HardwareSession):
    from PySide6.QtCore import Qt,QTimer,QEvent
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QGridLayout,QDoubleSpinBox,QFileDialog,QCheckBox,QMessageBox

    class HardwarePanel(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.role=role;self.calibration=None;self.binding=None;self.closing=False;self.sequence=-1
            self.shutdown_complete=False
            self.preview_pending=False;self.preview_generation=0
            self.session=session_factory(candidate,role)
            self.setWindowTitle('SO-101 hardware · '+role+' · '+candidate.port)
            self.resize(920,570);self.setModal(False)
            layout=QVBoxLayout(self)
            note=QLabel('Physical USB controls · Connect reads only. Import this arm’s LeRobot calibration before enabling motors. Hold Move to execute targets; release to hold position. Stop releases torque — support the arm. Keep the motor power switch accessible.')
            note.setWordWrap(True);layout.addWidget(note)
            row=QHBoxLayout();layout.addLayout(row)
            self.connect_button=QPushButton('Connect read-only');self.connect_button.clicked.connect(lambda:self.request('connect'));row.addWidget(self.connect_button)
            self.disconnect_button=QPushButton('Disconnect');self.disconnect_button.clicked.connect(self.disconnect);row.addWidget(self.disconnect_button)
            self.import_button=QPushButton('Import LeRobot calibration…');self.import_button.clicked.connect(self.import_calibration);row.addWidget(self.import_button)
            self.status=QLabel('Disconnected');self.status.setWordWrap(True);layout.addWidget(self.status)
            self.calibration_label=QLabel('No calibration loaded — raw reads only');layout.addWidget(self.calibration_label)
            grid=QGridLayout();layout.addLayout(grid)
            for col,text in enumerate(('Joint','Encoder','Measured','°C / V','Torque','Target','')):grid.addWidget(QLabel(text),0,col)
            self.readings={};self.targets={};self.send_buttons={}
            for row,name in enumerate(JOINT_NAMES,1):
                grid.addWidget(QLabel(name.replace('_',' ').title()),row,0)
                for col in range(1,5):
                    label=QLabel('—');self.readings[name,col]=label;grid.addWidget(label,row,col)
                target=QDoubleSpinBox();target.setDecimals(2);target.setKeyboardTracking(False);target.setRange(-180,180)
                target.setSuffix(' %' if name=='gripper' else '°');target.setSingleStep(1)
                self.targets[name]=target;grid.addWidget(target,row,5)
                button=QPushButton('Set target');button.clicked.connect(lambda checked=False,n=name:self.request('target',{n:self.targets[n].value()}))
                self.send_buttons[name]=button;grid.addWidget(button,row,6)
            row=QHBoxLayout();layout.addLayout(row)
            self.arm_button=QPushButton('Enable motors (hold current pose)');self.arm_button.clicked.connect(self.arm);row.addWidget(self.arm_button)
            self.move_button=QPushButton('Hold to move to targets');self.move_button.setAutoRepeat(False)
            self.move_button.pressed.connect(lambda:self.session.heartbeat(True));self.move_button.released.connect(lambda:self.session.heartbeat(False));row.addWidget(self.move_button)
            self.stop_button=QPushButton('STOP — release torque');self.stop_button.setStyleSheet('background: #9d2929; color: white; font-weight: bold;')
            self.stop_button.clicked.connect(lambda:self.session.stop());row.addWidget(self.stop_button)
            self.binding_label=QLabel('No measured virtual binding');layout.addWidget(self.binding_label)
            row=QHBoxLayout();layout.addLayout(row)
            self.capture_button=QPushButton('Measure virtual binding…');self.capture_button.clicked.connect(self.capture_binding);row.addWidget(self.capture_button)
            self.binding_button=QPushButton('Load virtual binding…');self.binding_button.clicked.connect(self.import_binding);row.addWidget(self.binding_button)
            self.virtual_button=QPushButton('Use virtual pose as targets');self.virtual_button.clicked.connect(self.virtual_targets);row.addWidget(self.virtual_button)
            self.live=QCheckBox('Show measured physical joints in the scene (pauses simulation)');self.live.toggled.connect(self.live_changed);layout.addWidget(self.live)
            self.message=QLabel();self.message.setWordWrap(True);layout.addWidget(self.message)
            self._last_state='';self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)
            self.poll()

        def request(self,command,payload=None):
            try:self.session.request(command,payload);self.message.clear()
            except Exception as exc:self.message.setText(str(exc))

        def import_calibration(self):
            path,_=QFileDialog.getOpenFileName(self,'Open this arm’s LeRobot calibration','','JSON (*.json)')
            if not path:return
            try:
                calibration=Calibration.load(path)
                self.session.request('calibration',calibration)
                self.live.setChecked(False);self.calibration=calibration;self.binding=None
                self.calibration_label.setText('Calibration imported; register match required on connection: '+calibration.identity[:12])
                self.binding_label.setText('No measured virtual binding')
                for name,spin in self.targets.items():spin.setRange(*calibration.limits(name))
            except Exception as exc:self.message.setText(str(exc))

        def arm(self):
            if QMessageBox.question(self,'Enable physical motors',
                'Enable torque on this physical '+role+' arm and hold its measured pose? Clear the workspace and keep motor power within reach.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                self.request('arm')

        def import_binding(self):
            if not self.calibration:return
            path,_=QFileDialog.getOpenFileName(self,'Open measured joint binding','','JSON (*.json)')
            if not path:return
            try:
                self.binding=load_binding(path,role,self.session.device_id,self.calibration)
                self.binding_label.setText('Measured binding loaded: '+role)
            except Exception as exc:self.message.setText(str(exc))

        def capture_binding(self):
            if not self.calibration:return
            from .binding_ui import build_binding_dialog
            dialog=build_binding_dialog(self);dialog.exec();dialog.deleteLater()

        def virtual_targets(self):
            try:
                positions=owner.robot_panel.state.get('positions',{}).get(role)
                if not self.binding or not positions:raise ValueError('Load a measured binding and a matching virtual arm first')
                if self.binding.device_id!=self.session.device_id or self.binding.calibration_id!=self.calibration.identity:
                    raise ValueError('The device session or calibration changed; measure or load its binding again')
                if self.live.isChecked():raise ValueError('Turn off live view and pose the simulated arm before loading targets')
                values=binding_targets(self.binding,positions)
                self.session.request('target',values)
                for name,value in values.items():self.targets[name].setValue(value)
                self.message.setText('Virtual pose loaded as targets. Hold Move to execute; no motion starts from this action.')
            except Exception as exc:self.message.setText(str(exc))

        def live_changed(self,enabled):
            self.preview_generation+=1;self.sequence=-1
            if not enabled:
                self.sequence=-1
                if owner.worker and owner._ready:
                    owner._command(lambda:owner.worker.release_hardware(role),owner._apply_status)

        def disconnect(self):
            self.live.setChecked(False);self.session.stop(disconnect=True,force=False)

        def poll(self):
            self.session.heartbeat(self.move_button.isDown() and not self.closing and self.isActiveWindow())
            snapshot=self.session.snapshot();state=snapshot['state'];sample=snapshot['sample']
            stale=snapshot['stale'];armed=state=='armed' and not stale
            self.status.setText(state.upper()+(' · STALE' if stale else '')+(' · '+snapshot['error'] if snapshot['error'] else ''))
            self.connect_button.setEnabled(state in ('disconnected','fault') and not self.closing)
            self.import_button.setEnabled(state not in ('armed','arming','connecting') and not self.closing)
            healthy=bool(sample and not stale and sample['observations'] and not sample['calibration_error'])
            self.arm_button.setEnabled(state=='read-only' and healthy and not any(m['torque'] for m in sample['motors'].values()))
            self.move_button.setEnabled(armed);self.virtual_button.setEnabled(armed and bool(self.binding))
            self.binding_button.setEnabled(bool(self.calibration) and not armed)
            self.capture_button.setEnabled(state=='read-only' and healthy)
            self.live.setEnabled(healthy and bool(self.binding) and owner._ready)
            if sample:
                for i,name in enumerate(JOINT_NAMES,1):
                    motor=sample['motors'][i];value=sample['observations'].get(name)
                    self.readings[name,1].setText(str(motor['position']))
                    self.readings[name,2].setText('—' if value is None else f'{value:.2f}'+(' %' if name=='gripper' else '°'))
                    self.readings[name,3].setText(f"{motor['temperature']} / {motor['voltage']:.1f}")
                    self.readings[name,4].setText('ON' if motor['torque'] else 'off')
                    if state!=self._last_state and value is not None:self.targets[name].setValue(value)
                if sample['calibration_error']:self.message.setText(sample['calibration_error'])
            else:
                for label in self.readings.values():label.setText('—')
            for name,button in self.send_buttons.items():button.setEnabled(armed)
            for spin in self.targets.values():spin.setEnabled(armed)
            self._last_state=state
            if self.live.isChecked():
                if not healthy or state not in ('read-only','armed'):
                    self.live.setChecked(False);self.message.setText('Live view stopped: physical telemetry is unavailable or stale.')
                elif sample['sequence']!=self.sequence and not self.preview_pending and owner._ready:
                    try:
                        self.sequence=sample['sequence']
                        generation=self.preview_generation;binding=self.binding;calibration=self.calibration
                        self.preview_pending=True
                        def publish():
                            try:
                                if generation!=self.preview_generation:return {'hardware_cancelled':True}
                                latest=self.session.snapshot();current=latest['sample']
                                if latest['stale'] or latest['state'] not in ('read-only','armed') or not current or current['calibration_error']:
                                    raise ValueError('Live view stopped: physical telemetry is unavailable or stale.')
                                mapped=binding.map_observation({n+'.pos':v for n,v in current['observations'].items()},
                                    device_id=self.session.device_id,calibration_id=calibration.identity,
                                    captured_at=current['timestamp'],now=time.monotonic())
                                positions={path.rsplit('/',1)[-1]:v for path,v in mapped.items()}
                                return owner.worker.hardware_pose(role,positions,current['timestamp'])
                            except Exception as exc:return {'hardware_error':str(exc)}
                        def displayed(frame):
                            self.preview_pending=False
                            if generation!=self.preview_generation or frame.get('hardware_cancelled'):return
                            if 'hardware_error' in frame:
                                self.live.setChecked(False);self.message.setText(frame['hardware_error'])
                            elif self.live.isChecked():owner._accept_frame(frame)
                        owner._command(publish,displayed)
                    except Exception as exc:
                        self.preview_pending=False
                        self.live.setChecked(False);self.message.setText(str(exc))
            if self.closing and not snapshot['alive']:
                self.timer.stop()
                if snapshot['stop_confirmed'] is False:
                    QMessageBox.critical(self,'Motor stop unconfirmed',
                        'The bus did not confirm torque-off. Use the physical motor power switch and support the arm.\n\n'+snapshot['error'])
                self.shutdown_complete=True;self.done(0)

        def event(self,event):
            if event.type()==QEvent.Type.WindowDeactivate and hasattr(self,'move_button'):
                self.move_button.setDown(False);self.session.heartbeat(False)
            return super().event(event)

        def shutdown(self):
            self.closing=True;self.move_button.setDown(False);self.live.setChecked(False)
            self.session.stop(shutdown=True,force=False)

        def closeEvent(self,event):
            if not self.session._thread.is_alive():event.accept();return
            event.ignore();self.shutdown()

        def reject(self):
            self.close()

    return HardwarePanel()
