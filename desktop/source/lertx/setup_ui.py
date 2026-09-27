"""Guided SO-101 setup with torque-off calibration and visible measured preview."""
import math,time
from pathlib import Path
from uuid import uuid4
from .devices import scan_result,RoleAssignments
from .transport import ConnectionProbe
from .hardware import HardwareSession
from .robot import JOINT_NAMES
from .setup_calibration import RangeCapture,reference_pose,save_json
from .hardware_calibration import save_binding

JOINT_HELP={
 'shoulder_pan':'Turn the base left and right. The upper arm should rotate around the upright base axis.',
 'shoulder_lift':'Support the arm and lift/lower the upper arm at the shoulder.',
 'elbow_flex':'Support the forearm and bend/straighten the elbow.',
 'wrist_flex':'Tilt the wrist up and down, keeping the other joints still.',
 'wrist_roll':'Roll the wrist gently in both directions. Do not twist the cable around the arm. LeRobot uses the full 0–4095 range for this joint; the twin binding uses only your observed travel.',
 'gripper':'Open and close the claw by hand (leader: squeeze/release the trigger). Do not force the mechanism.'}


def build_setup_wizard(owner,session_factory=HardwareSession,scanner=None):
    from PySide6.QtCore import Qt,QTimer
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QProgressBar,QMessageBox
    class SetupWizard(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.setWindowTitle('Set up a real SO-101 arm');self.resize(560,720);self.setModal(False)
            self.session=None;self.step=0;self.capture=None;self.candidate=None;self.role='follower'
            self.closing=False;self.shutdown_complete=False;self.transferred=False;self.pending=False
            self.guide_ready=False;self.preview_step=None;self.guide_shown=False;self.sequence=-1;self.preview_pending=False;self.preview_generation=0;self.observation=None
            self.probe=scanner or ConnectionProbe(scan_result);self.ticket=None;self.candidates=[]
            self.run_dir=Path(owner.config_path).parent/'calibration'/uuid4().hex
            layout=QVBoxLayout(self)
            self.heading=QLabel();self.heading.setStyleSheet('font-size: 20px; font-weight: bold;');layout.addWidget(self.heading)
            self.progress=QProgressBar();self.progress.setRange(0,10);layout.addWidget(self.progress)
            self.instructions=QLabel();self.instructions.setWordWrap(True);layout.addWidget(self.instructions)
            self.role_box=QComboBox();self.role_box.addItems(['follower','leader']);layout.addWidget(self.role_box)
            self.ports=QComboBox();layout.addWidget(self.ports)
            self.scan_button=QPushButton('Refresh USB ports');self.scan_button.clicked.connect(self.scan);layout.addWidget(self.scan_button)
            self.support=QCheckBox('The arm is supported and I can reach its power switch');layout.addWidget(self.support)
            self.release=QPushButton('Release torque so I can move the arm by hand');self.release.clicked.connect(self.release_torque);layout.addWidget(self.release)
            self.reference_check=QCheckBox('The real arm matches the reference pose shown in the viewport');layout.addWidget(self.reference_check)
            self.direction=QCheckBox('Reverse this joint in the preview');self.direction.toggled.connect(self.reverse);layout.addWidget(self.direction)
            self.confirm=QCheckBox('I moved through the travel and the virtual joint follows the correct direction');layout.addWidget(self.confirm)
            self.live=QCheckBox('Mirror measured movement in the viewport');self.live.setChecked(True);self.live.toggled.connect(self.live_changed);layout.addWidget(self.live)
            self.readings=QLabel();self.readings.setWordWrap(True);self.readings.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.readings)
            self.connection=QLabel();self.connection.setWordWrap(True);layout.addWidget(self.connection)
            self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
            self.preview_status=QLabel();self.preview_status.setWordWrap(True);layout.addWidget(self.preview_status)
            self.next_button=QPushButton();self.next_button.clicked.connect(self.advance);layout.addWidget(self.next_button)
            self.cancel_button=QPushButton('Cancel setup');self.cancel_button.clicked.connect(self.close);layout.addWidget(self.cancel_button)
            self.reset_button=QPushButton('Start again after a connection fault');self.reset_button.clicked.connect(self.restart);layout.addWidget(self.reset_button);self.reset_button.hide()
            self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)
            self.render_step();self.scan()

        def render_step(self):
            self.status.clear()
            names=['Choose arm and USB port','Check the arm and release torque','Match the reference pose']+[n.replace('_',' ').title() for n in JOINT_NAMES]+['Review and save','Setup complete']
            self.heading.setText(f'{min(self.step+1,11)} / 11 · '+names[self.step]);self.progress.setValue(self.step)
            joint=3<=self.step<=8
            for widget in (self.role_box,self.ports,self.scan_button):widget.setVisible(self.step==0)
            self.support.setVisible(self.step==1);self.release.setVisible(self.step==1)
            self.reference_check.setVisible(self.step==2)
            self.direction.setVisible(joint);self.confirm.setVisible(joint)
            self.live.setVisible(self.step>=3)
            self.confirm.setChecked(False)
            if joint:
                n=JOINT_NAMES[self.step-3]
                self.direction.blockSignals(True);self.direction.setChecked(self.capture.directions[n]<0);self.direction.blockSignals(False)
                text=JOINT_HELP[n]+' Move one joint at a time, slowly, through its comfortable mechanical travel. Watch the matching link in the viewport. If it moves backwards, reverse it here. Stop at the mechanical limit; never force it.'
                self.next_button.setText('Confirm this joint and continue')
            elif self.step==0:
                text='For an assembled SO-101 with motor IDs 1–6 already assigned at 1 Mbps: connect one arm’s USB cable and motor power. Choose whether this is the follower (robot hand) or leader (hand-operated controller). If the port is unclear, unplug its USB cable, refresh, then reconnect and refresh. Connection reads registers only; it never enables motors.'
                self.next_button.setText('Connect and check six motors')
            elif self.step==1:
                text='The arm must be assembled with STS3215 motor IDs 1–6 at 1 Mbps. Support it before releasing torque. If a motor is missing, check power/cables and its ID; newly unconfigured motors must be assigned individually before calibration.'
                self.next_button.setText('Show the reference pose')
            elif self.step==2:
                text='Align the real arm with the reference: upper arm upright, forearm approximately horizontal, wrist straight, claw facing forward and halfway open (leader trigger halfway). Center base rotation and wrist roll. The viewport currently shows a guide, not telemetry. The next action backs up existing calibration and writes LeRobot half-turn homing offsets. Hold the pose still.'
                self.next_button.setText('Capture reference and begin calibration')
            elif self.step==9:
                text='All six joints are recorded. Review the travel and mirrored direction. Save writes the measured limits to the arm and exports LeRobot calibration plus its virtual binding. Motors remain off. The backup permits recovery if calibration is interrupted.'
                self.next_button.setText('Save calibration to arm and files')
            else:
                text='Calibration is saved and verified against the arm. Continue to hardware controls for measured live view. Motor enabling and held movement remain separate explicit actions. Repeat setup for the other arm.'
                self.next_button.setText('Finish and open live hardware controls')
            self.instructions.setText(text)
            if self.step in (0,1):
                self.instructions.setText(text+'<br><br><a href="https://huggingface.co/docs/lerobot/so101">New motors? Follow the official wiring and individual motor-ID setup guide first.</a>')
                self.instructions.setOpenExternalLinks(True)

        def scan(self):
            if self.ticket is None:
                self.ticket=self.probe.start(());self.scan_button.setEnabled(False)
        def release_torque(self):
            if self.session and self.support.isChecked():self.session.stop(force=True)
            else:self.status.setText('Confirm that the arm is supported first.')
        def advance(self):
            try:
                if self.step==0:
                    if not self.candidates:raise ValueError('No USB arm found. Connect USB and power, then refresh.')
                    self.candidate=self.candidates[self.ports.currentIndex()];self.role=self.role_box.currentText()
                    for panel in owner._hardware_windows.values():
                        if panel is not self and panel.session._thread.is_alive() and panel.session.candidate.attachment==self.candidate.attachment:
                            raise ValueError('Close the existing hardware panel for this USB port first.')
                    roles=RoleAssignments(Path(owner.config_path).parent/'devices.json')
                    roles.assign(self.role,self.candidate,self.candidates)
                    self.session=session_factory(self.candidate,self.role);owner._hardware_windows['setup']=self
                    self.session.request('connect');self.pending=True;self.step=1;self.render_step()
                elif self.step==1:
                    self.require_sample()
                    if not self.support.isChecked():raise ValueError('Confirm that the arm is supported.')
                    self.step=2;self.render_step()
                elif self.step==2:
                    self.require_sample()
                    if not self.guide_ready:raise ValueError('Wait for the reference pose to appear in the robot viewport first.')
                    if not self.reference_check.isChecked():raise ValueError('Match the reference pose and confirm it first.')
                    self.session.request('setup_begin',self.run_dir/'original-registers.json');self.pending=True
                    self.status.setText('Backing up registers and setting homing offsets… hold the arm still.')
                elif 3<=self.step<=8:
                    self.require_sample()
                    if not self.live.isChecked() or self.preview_step!=self.step:raise ValueError('Wait for this joint’s measured movement to appear in the viewport first.')
                    if not self.confirm.isChecked():raise ValueError('Verify the range and mirrored direction before continuing.')
                    self.capture.confirm(JOINT_NAMES[self.step-3]);self.step+=1;self.render_step()
                elif self.step==9:
                    self.require_sample();cal=self.capture.calibration();binding=self.capture.binding(self.session.device_id)
                    # Save pending artifacts before the hardware commit; never mark them accepted yet.
                    save_json(self.run_dir/'pending-calibration.json',cal.values)
                    save_binding(self.run_dir/'pending-binding.json',binding)
                    self.session.request('setup_save',cal);self.pending=True
                elif self.step==10:self.finish_setup()
            except Exception as exc:self.status.setText(str(exc))

        def require_sample(self):
            s=self.session.snapshot() if self.session else {};sample=s.get('sample')
            if not sample or s['stale'] or s['state'] not in ('read-only','calibrating'):
                raise ValueError('Wait for a fresh, complete connection to the six motors.')
            if any(m['torque'] for m in sample['motors'].values()):raise ValueError('Release motor torque before continuing.')
            return sample
        def reverse(self,checked):
            if self.capture and 3<=self.step<=8:
                self.capture.directions[JOINT_NAMES[self.step-3]]=-1 if checked else 1
                self.confirm.setChecked(False);self.sequence=-1;self.preview_step=None
        def live_changed(self,enabled):
            self.sequence=-1;self.preview_generation+=1
            if not enabled and owner.worker and owner._ready:
                owner._command(lambda:owner.worker.release_hardware(self.role),owner._apply_status)
        def publish(self,positions,timestamp):
            if owner._pending or not owner._ready or self.preview_pending:return
            generation=self.preview_generation;issued_step=self.step;self.preview_pending=True
            def work():
                try:
                    selected=None
                    if self.capture and 3<=self.step<=8 and hasattr(owner.worker,'select_joint'):
                        selected=owner.worker.select_joint(self.role,JOINT_NAMES[self.step-3])
                    frame=owner.worker.setup_pose(self.role,positions,timestamp)
                    if selected:frame['setup_selection']=selected
                    return frame
                except Exception as exc:return {'setup_error':str(exc)}
            def done(frame):
                self.preview_pending=False
                if generation!=self.preview_generation:return
                if 'setup_error' in frame:
                    self.preview_status.setText(frame['setup_error'])
                    if timestamp is None:self.guide_shown=False
                else:
                    owner._accept_frame(frame)
                    if frame.get('setup_selection'):owner.robot_panel.select_joint(frame['setup_selection'])
                    if timestamp is None:self.guide_ready=True
                    elif issued_step==self.step:self.preview_step=issued_step
            owner._command(work,done)
            return True
        def finish_setup(self):
            from .hardware_ui import build_hardware_panel
            panel=build_hardware_panel(owner,self.candidate,self.role,session_factory=lambda *a:self.session)
            panel.calibration=self.capture.calibration();panel.binding=self.capture.binding(self.session.device_id)
            for n,spin in panel.targets.items():spin.setRange(*panel.calibration.limits(n))
            panel.calibration_label.setText('Wizard calibration verified · '+str(self.run_dir/'calibration.json'))
            panel.binding_label.setText('Verified reference and joint directions loaded')
            owner._hardware_windows.pop('setup',None);owner._hardware_windows[self.role]=panel
            self.transferred=True;self.timer.stop();self.preview_generation+=1
            panel.live.setChecked(True);panel.show();self.done(1)
        def restart(self):
            if self.session and self.session._thread.is_alive():
                self.session.stop(shutdown=True,force=False);self.status.setText('Closing the previous connection; click again when it has stopped.');return
            owner._hardware_windows.pop('setup',None)
            self.session=None;self.capture=None;self.step=0;self.pending=False
            self.guide_ready=False;self.preview_step=None;self.guide_shown=False;self.sequence=-1;self.preview_generation+=1
            self.reference_check.setChecked(False);self.support.setChecked(False);self.live.setChecked(True)
            self.run_dir=Path(owner.config_path).parent/'calibration'/uuid4().hex
            self.status.clear();self.connection.clear();self.preview_status.clear();self.readings.clear()
            self.reset_button.hide();self.render_step();self.scan()
        def poll(self):
            if self.ticket is not None:
                result=self.probe.poll(self.ticket)
                if result is not None:
                    self.ticket=None;self.scan_button.setEnabled(True);self.ports.clear()
                    self.candidates=result.get('candidates',[])
                    for c in self.candidates:self.ports.addItem(c.port+' · '+c.description+(' · '+c.serial if c.serial else ' · no unique serial'))
                    self.status.setText('Choose the port for this arm.' if self.candidates else 'No USB ports found. Check the cable, motor power and USB driver, then refresh.')
            if not self.session:
                self.next_button.setEnabled(bool(self.candidates));return
            self.session.heartbeat(False);s=self.session.snapshot();sample=s['sample'];setup=s.get('setup') or {}
            if self.closing:
                if not s['alive']:
                    self.timer.stop();self.shutdown_complete=True
                    if setup.get('state')=='restore-unconfirmed' or s['stop_confirmed'] is False:
                        QMessageBox.critical(self,'Setup recovery required',s['error']+'\nBackup: '+str(self.run_dir/'original-registers.json'))
                    self.done(0)
                return
            self.next_button.setEnabled(not self.pending and bool(sample) and not s['stale'])
            if s['state']=='fault':
                self.pending=False;self.status.setText(s['error']);self.next_button.setEnabled(False);self.reset_button.show()
                if self.live.isChecked():self.live.setChecked(False)
                return
            if self.step==1 and s['state']=='read-only':self.pending=False
            if self.step==2 and setup.get('state')=='recording':
                self.capture=RangeCapture(self.role,setup['homings']);self.pending=False;self.step=3;self.render_step()
            if self.step==9 and setup.get('state')=='saved':
                try:
                    save_json(self.run_dir/'calibration.json',self.capture.calibration().values)
                    save_binding(self.run_dir/'binding.json',self.capture.binding(self.session.device_id))
                    save_json(self.run_dir/'setup.json',dict(schema=1,role=self.role,device_id=self.session.device_id,calibration_id=self.capture.calibration().identity))
                    self.pending=False;self.step=10;self.render_step()
                except Exception as exc:self.status.setText('Calibration is on the arm but saving files failed: '+str(exc));return
            if sample and not s['stale']:
                if self.capture and 3<=self.step<=8:
                    n=JOINT_NAMES[self.step-3]
                    try:self.capture.observe(sample,n)
                    except ValueError as exc:self.status.setText(str(exc));self.next_button.setEnabled(False);return
                    low,high=self.capture.ranges[n]
                    self.readings.setText(f'Motor {self.step-2} · {n.replace("_"," ")}\nEncoder now: {sample["motors"][self.step-2]["position"]}\nRecorded travel: {low} → {high} ({high-low} ticks)')
                elif self.capture:self.readings.setText('\n'.join(n.replace('_',' ')+': '+str(self.capture.ranges[n]) for n in JOINT_NAMES))
                else:self.readings.setText('\n'.join(f'Motor {i} · {JOINT_NAMES[i-1]} · encoder {m["position"]} · torque '+('ON' if m['torque'] else 'off') for i,m in sample['motors'].items()))
                if self.capture and self.live.isChecked() and sample['sequence']!=self.sequence and not owner._pending:
                    positions,clipped=self.capture.preview(sample);self.sequence=sample['sequence']
                    self.preview_status.setText('CALIBRATION PREVIEW · reference and direction require your verification'+('\nVirtual limits reached: '+', '.join(clipped) if clipped else ''))
                    self.publish(positions,sample['timestamp'])
                elif self.step==2 and not self.pending and not owner._pending and not self.guide_shown:
                    self.guide_shown=bool(self.publish(reference_pose(self.role),None))
                if not self.pending:self.connection.setText('Connected · motors remain off' if not any(m['torque'] for m in sample['motors'].values()) else 'Torque is ON. Support the arm and release torque.')
            elif s['stale']:
                self.preview_status.setText('Telemetry is stale. Mirroring stopped.');self.next_button.setEnabled(False)
        def shutdown(self):
            self.closing=True;self.live.setChecked(False);self.preview_generation+=1
            if self.session:self.session.stop(shutdown=True,force=False)
            else:self.timer.stop();self.shutdown_complete=True;self.done(0)
        def closeEvent(self,event):
            if self.transferred or self.shutdown_complete:event.accept();return
            event.ignore();self.shutdown()
        def reject(self):self.close()
    return SetupWizard()
