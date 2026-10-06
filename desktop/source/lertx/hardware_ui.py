"""Explicit hardware connection, telemetry, arming and held manual motion."""
import math
import time
from .robot import JOINT_NAMES
from .hardware import HardwareSession
from .hardware_calibration import Calibration, load_binding, binding_targets
from .hardware_feedback import torque_summary,arming_blocker


def build_hardware_panel(owner,candidate,role,session_factory=HardwareSession):
    from PySide6.QtCore import Qt,QTimer,QEvent
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QGridLayout,QDoubleSpinBox,QFileDialog,QCheckBox,QMessageBox

    from .role_ui import widgets
    QLabel,QPushButton,QCheckBox=widgets(lambda: owner.profile)
    access=owner.devices.acquire(candidate,role,"hardware",session_factory)

    class HardwarePanel(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.role=role;self.closing=False;self.sequence=-1
            self.shutdown_complete=False;self.return_to_devices=False
            self.finished.connect(self.return_to_parent)
            self.preview_pending=False;self.preview_generation=0
            self.preview_at=0.
            self.motor_action=None;self.motor_sequence=-1
            self.session=access
            self.setWindowTitle('SO-101 hardware · '+role+' · '+candidate.port)
            from .role_ui import role_icon
            self.setWindowIcon(role_icon(role,owner.profile))
            self.resize(920,570);self.setModal(False)
            layout=QVBoxLayout(self)
            self.parent_button=QPushButton('Back to Device Manager')
            self.parent_button.clicked.connect(self.back_to_devices);layout.addWidget(self.parent_button)
            layout.addWidget(QLabel(role.capitalize()+' · physical USB controls'))
            note=QLabel('Physical USB controls · Connect reads only. Import this arm’s LeRobot calibration before engaging motors. Hold Move to execute targets; release the button to hold position. Release motors makes the arm free — support it. Keep the motor power switch accessible.')
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
            self.torque_status=QLabel();self.torque_status.setWordWrap(True);layout.addWidget(self.torque_status)
            row=QHBoxLayout();layout.addLayout(row)
            self.torque_button=QPushButton();self.torque_button.clicked.connect(self.toggle_torque);row.addWidget(self.torque_button)
            self.move_button=QPushButton('Hold to move to targets');self.move_button.setAutoRepeat(False)
            self.move_button.pressed.connect(lambda:self.session.heartbeat(True));self.move_button.released.connect(lambda:self.session.heartbeat(False));row.addWidget(self.move_button)
            self.motor_reason=QLabel();self.motor_reason.setWordWrap(True);layout.addWidget(self.motor_reason)
            self.motor_result=QLabel();self.motor_result.setWordWrap(True);layout.addWidget(self.motor_result)
            self.binding_label=QLabel('No measured virtual binding');layout.addWidget(self.binding_label)
            row=QHBoxLayout();layout.addLayout(row)
            self.capture_button=QPushButton('Measure virtual binding…');self.capture_button.clicked.connect(self.capture_binding);row.addWidget(self.capture_button)
            self.binding_button=QPushButton('Load virtual binding…');self.binding_button.clicked.connect(self.import_binding);row.addWidget(self.binding_button)
            self.virtual_button=QPushButton('Use virtual pose as targets');self.virtual_button.clicked.connect(self.virtual_targets);row.addWidget(self.virtual_button)
            self.live=QCheckBox('Show measured physical joints in the scene (pauses simulation)');self.live.toggled.connect(self.live_changed);layout.addWidget(self.live)
            self.live_reason=QLabel();self.live_reason.setWordWrap(True);layout.addWidget(self.live_reason)
            self.message=QLabel();self.message.setWordWrap(True);layout.addWidget(self.message)
            self._last_state='';self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)
            self.poll()

        @property
        def calibration(self):return self.session.controller.calibration
        @calibration.setter
        def calibration(self,value):self.session.controller.calibration=value
        @property
        def binding(self):return self.session.controller.binding
        @binding.setter
        def binding(self,value):self.session.controller.binding=value

        def request(self,command,payload=None):
            try:self.session.request(command,payload);self.message.clear();return True
            except Exception as exc:self.message.setText(str(exc));return False

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

        def toggle_torque(self):
            snapshot=self.session.snapshot();sample=snapshot['sample']
            if self.motor_action=='arm' or snapshot['state'] in ('armed','arming') or (sample and any(m['torque'] for m in sample['motors'].values())):
                self.release_torque()
            elif not self.motor_action:self.arm()

        def arm(self):
            reason=arming_blocker(self.session.snapshot())
            if reason or self.motor_action:
                self.motor_result.setText(reason or 'Wait for the pending motor operation.');return
            if QMessageBox.question(self,'Enable physical motors',
                'Enable torque on this physical '+role+' arm and hold its measured pose? Clear the workspace and keep motor power within reach.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                if self.request('arm'):
                    self.motor_action='arm';self.motor_result.setText('Enabling motors… checking the current pose and all six torque registers.')
                    self.torque_button.setText('Cancel engaging · release motors')
            else:self.motor_result.setText('Enabling cancelled — no torque command sent.')

        def release_torque(self):
            snapshot=self.session.snapshot();sample=snapshot['sample']
            if not sample:
                self.motor_result.setText('Release not confirmed — no motor connection. Connect read-only first; use the motor power switch if torque may still be on.')
                return
            self.motor_action='stop';self.motor_sequence=sample['sequence']
            self.move_button.setDown(False);self.stop_request=self.session.stop()
            self.motor_result.setText('Releasing torque… waiting for all six motors to confirm OFF. Support the arm.')
            self.torque_button.setEnabled(False);self.torque_button.setText('Releasing motors…')

        def update_motor_feedback(self,snapshot):
            sample=snapshot['sample'];state=snapshot['state'];stale=snapshot['stale']
            self.torque_status.setText(torque_summary(snapshot))
            if self.motor_action:
                if state=='fault' or (self.motor_action=='stop' and snapshot['stop_confirmed'] is False):
                    self.motor_result.setText(('Release unconfirmed: ' if self.motor_action=='stop' else 'Enable failed: ')+snapshot['error'])
                    self.motor_action=None
                elif self.motor_action=='arm' and state=='armed' and sample and not stale and all(m['torque'] for m in sample['motors'].values()):
                    self.motor_result.setText('Last action: Enabled and verified · all 6 motors holding the measured pose. No target movement starts until you hold Move.')
                    self.motor_action=None
                elif self.motor_action=='stop' and snapshot['stop_completed']>=self.stop_request and sample and not stale and sample['sequence']>self.motor_sequence and snapshot['stop_confirmed'] is True and not any(m['torque'] for m in sample['motors'].values()):
                    self.motor_result.setText('Last action: Released and verified · all 6 motors OFF. Already-off motors will not visibly change.')
                    self.motor_action=None

            reason=arming_blocker(snapshot)
            available=not reason and not self.motor_action and not self.closing
            release=bool(sample and any(m['torque'] for m in sample['motors'].values())) or state in ('armed','arming') or self.motor_action=='arm'
            self.torque_button.setEnabled((available or release) and self.motor_action!='stop' and not self.closing)
            self.torque_button.setText('Releasing motors…' if self.motor_action=='stop' else
                'Cancel engaging · release motors' if self.motor_action=='arm' or state=='arming' else
                'Release motors · move by hand' if release else
                'Engage motors · hold current pose' if available else 'Engage motors — unavailable')
            self.torque_button.setStyleSheet('QPushButton:enabled { background: #9d2929; color: white; font-weight: bold; }' if release else '')
            self.motor_reason.setText('Support the arm before releasing; it will no longer hold itself.' if release else
                ('Engage unavailable: '+reason) if reason and state!='armed' else
                reason or ('Wait for the pending motor operation.' if self.motor_action else 'Ready to enable: the arm will hold its current pose after confirmation.'))
            self.torque_button.setToolTip(self.motor_reason.text())

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
            if hasattr(self,'preview_window') and not self.preview_window.disposed:
                self.preview_window.set_mode('paused' if not self.live.isChecked() else 'stale' if not healthy else 'live' if time.monotonic()-self.preview_at<1. else 'waiting')
                self.preview_window.status.setText('Measured physical motion · NVIDIA RTX' if self.live.isChecked() and healthy else
                    'Physical mirroring paused · '+(snapshot['error'] or ('telemetry stale' if stale else state)))
            self.update_motor_feedback(snapshot)
            self.move_button.setEnabled(armed);self.virtual_button.setEnabled(armed and bool(self.binding))
            self.binding_button.setEnabled(bool(self.calibration) and not armed)
            self.capture_button.setEnabled(state=='read-only' and healthy)
            self.live.setEnabled(healthy and bool(self.binding) and owner._ready)
            self.live_reason.setText('3D mirroring unavailable: complete setup for this '+role+' or import its calibration.' if not self.calibration else
                '3D mirroring unavailable: measure or load this arm’s virtual binding, or complete guided setup.' if not self.binding else
                '3D mirroring waiting for fresh calibrated readings. '+(sample['calibration_error'] if sample else '') if not healthy else
                '3D mirroring waiting for the RTX workspace.' if not owner._ready else
                'Live measured motion is enabled.' if self.live.isChecked() else 'Mirroring paused — check the box above to follow this physical arm.')
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
            if not snapshot['control_available'] and not self.closing:
                self.status.setText(state.upper()+' · controlled by '+snapshot['control_owner']+' · shared telemetry')
                for widget in (self.connect_button,self.disconnect_button,self.import_button,self.torque_button,
                        self.move_button,self.virtual_button,self.binding_button,self.capture_button,self.live,
                        *self.send_buttons.values(),*self.targets.values()):widget.setEnabled(False)
                self.live.setChecked(False)
            elif not self.closing:self.disconnect_button.setEnabled(True)
            if self.calibration:
                for name,spin in self.targets.items():spin.setRange(*self.calibration.limits(name))
            if self.live.isChecked():
                if not healthy or state not in ('read-only','armed'):
                    self.live.setChecked(False);self.message.setText('Live view stopped: physical telemetry is unavailable or stale.')
                elif (sample['sequence']!=self.sequence and not self.preview_pending and owner._ready
                      and time.monotonic()-getattr(self,'preview_requested_at',0.) >=
                      1/getattr(owner,'_debug_target_fps',owner.profile['rendering']['target_fps'])):
                    try:
                        self.preview_requested_at=time.monotonic()
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
                            elif self.live.isChecked():
                                owner._accept_frame(frame)
                                self.preview_at=time.monotonic()
                                if hasattr(self,'preview_window') and not self.preview_window.disposed:self.preview_window.set_mode('live')
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

        def back_to_devices(self):
            self.return_to_devices=True;self.parent_button.setEnabled(False);self.close()

        def return_to_parent(self,_):
            if self.return_to_devices and not owner.devices.closing:
                self.return_to_devices=False
                QTimer.singleShot(0,owner._on_devices)

        def event(self,event):
            if event.type()==QEvent.Type.WindowDeactivate and hasattr(self,'move_button'):
                self.move_button.setDown(False);self.session.heartbeat(False)
            return super().event(event)

        def shutdown(self):
            self.closing=True;self.move_button.setDown(False);self.live.setChecked(False)
            if hasattr(self,'preview_window'):self.preview_window.dispose()
            self.session.stop(shutdown=True,force=False)

        def closeEvent(self,event):
            if not self.session.alive:event.accept();return
            event.ignore();self.shutdown()

        def reject(self):
            self.close()

    try:return HardwarePanel()
    except Exception:
        access.stop(shutdown=True,force=False)
        raise
