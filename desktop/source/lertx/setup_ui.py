"""Guided SO-101 setup with torque-off calibration and visible measured preview."""
import math,time
from pathlib import Path
from uuid import uuid4
from .devices import scan_result,RoleAssignments
from .transport import ConnectionProbe
from .hardware import HardwareSession
from .robot import JOINT_NAMES,ROOTS
from .setup_calibration import RangeCapture,reference_pose,save_json
from .hardware_calibration import save_binding
from .setup_visuals import JOINT_GUIDES,JointMap,NativeSetupView

def build_setup_wizard(owner,session_factory=HardwareSession,scanner=None):
    from PySide6.QtCore import Qt,QTimer
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QProgressBar,QMessageBox,QWidget,QScrollArea
    class SetupWizard(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.setWindowTitle('SO-101 · guided arm setup');self.resize(1120,760);self.setModal(False)
            self.session=None;self.step=0;self.capture=None;self.candidate=None;self.role='follower'
            self.closing=False;self.shutdown_complete=False;self.transferred=False;self.pending=False
            self.guide_ready=False;self.preview_step=None;self.guide_shown=False;self.sequence=-1;self.preview_pending=False;self.preview_generation=0;self.observation=None
            self.preview_at=0.;self.preview_error='';self.last_raw=None;self.moved_at={};self.selected_joint=None
            self.probe=scanner or ConnectionProbe(scan_result);self.ticket=None;self.candidates=[]
            self.run_dir=Path(owner.config_path).parent/'calibration'/uuid4().hex
            outer=QVBoxLayout(self)
            title=QLabel('Meet your arm');title.setStyleSheet('font-size: 24px; font-weight: bold;');outer.addWidget(title)
            self.stage_label=QLabel('Connect  →  Prepare  →  Learn six joints  →  Save  →  Done');outer.addWidget(self.stage_label)
            body=QHBoxLayout();outer.addLayout(body,1)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setMinimumWidth(345);scroll.setMaximumWidth(430)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.controls_scroll=scroll
            controls=QWidget();layout=QVBoxLayout(controls);scroll.setWidget(controls);body.addWidget(scroll,2)
            visual=QVBoxLayout();body.addLayout(visual,3)
            self.preview_title=QLabel('Your arm in 3D');self.preview_title.setWordWrap(True);visual.addWidget(self.preview_title)
            self.native_view=NativeSetupView();visual.addWidget(self.native_view,1)
            self.preview_status=QLabel('Connect your arm to begin.');self.preview_status.setWordWrap(True);visual.addWidget(self.preview_status)
            self.map_title=QLabel('Find the joint · schematic side view, numbered from base to hand');self.map_title.setWordWrap(True);visual.addWidget(self.map_title)
            self.joint_map=JointMap();visual.addWidget(self.joint_map)
            key=QLabel('Gold: this step   ·   Green ring: movement detected   ·   Green number: confirmed');key.setWordWrap(True);visual.addWidget(key)
            self.heading=QLabel();self.heading.setWordWrap(True);self.heading.setStyleSheet('font-size: 20px; font-weight: bold;');layout.addWidget(self.heading)
            self.progress=QProgressBar();self.progress.setRange(0,10);layout.addWidget(self.progress)
            self.instructions=QLabel();self.instructions.setWordWrap(True);layout.addWidget(self.instructions)
            self.movement=QLabel();self.movement.setWordWrap(True);layout.addWidget(self.movement)
            self.travel=QProgressBar();self.travel.setRange(0,100);self.travel.setFormat('Waiting for travel');layout.addWidget(self.travel)
            self.role_box=QComboBox();self.role_box.addItems(['follower','leader']);layout.addWidget(self.role_box)
            self.ports=QComboBox();self.ports.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.ports.setMinimumContentsLength(12);layout.addWidget(self.ports)
            self.scan_button=QPushButton('Refresh USB ports');self.scan_button.clicked.connect(self.scan);layout.addWidget(self.scan_button)
            self.support=QCheckBox('Arm supported; power switch within reach');layout.addWidget(self.support)
            self.release=QPushButton('Release torque for hand movement');self.release.clicked.connect(self.release_torque);layout.addWidget(self.release)
            self.reference_check=QCheckBox('My arm matches the reference pose');layout.addWidget(self.reference_check)
            self.direction=QCheckBox('Reverse this joint in the preview');self.direction.toggled.connect(self.reverse);layout.addWidget(self.direction)
            self.confirm=QCheckBox('Full travel and direction checked');layout.addWidget(self.confirm)
            self.live=QCheckBox('Mirror my arm in 3D');self.live.setChecked(True);self.live.toggled.connect(self.live_changed);layout.addWidget(self.live)
            self.readings=QLabel();self.readings.setWordWrap(True);self.readings.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.readings)
            self.connection=QLabel();self.connection.setWordWrap(True);layout.addWidget(self.connection)
            self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
            layout.addStretch(1)
            footer=QHBoxLayout();outer.addLayout(footer)
            self.cancel_button=QPushButton('Cancel setup');self.cancel_button.clicked.connect(self.close);footer.addWidget(self.cancel_button)
            self.back_button=QPushButton('Back to previous joint');self.back_button.clicked.connect(self.go_back);footer.addWidget(self.back_button)
            footer.addStretch(1)
            self.next_button=QPushButton();self.next_button.setMinimumHeight(38);self.next_button.clicked.connect(self.advance);footer.addWidget(self.next_button)
            self.reset_button=QPushButton('Restart after connection fault');self.reset_button.clicked.connect(self.restart);layout.addWidget(self.reset_button);self.reset_button.hide()
            self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)
            self.render_step();self.scan()

        def render_step(self):
            self.status.clear()
            self.controls_scroll.verticalScrollBar().setValue(0)
            self.preview_step=None;self.preview_generation+=1;self.sequence=-1
            names=['Choose arm and USB port','Support the arm','Match the reference pose']+[JOINT_GUIDES[n][0] for n in JOINT_NAMES]+['Review all six joints','You are ready']
            joint=3<=self.step<=8
            active=JOINT_NAMES[self.step-3] if joint else None
            self.joint_map.set_state(active,confirmed=self.capture.confirmed if self.capture else ())
            self.travel.setVisible(joint);self.movement.setVisible(joint)
            self.movement.setText('Move the highlighted joint. Watch for its green movement ring.')
            self.travel.setValue(0)
            self.preview_title.setText(('Joint '+str(self.step-2)+' · '+JOINT_GUIDES[active][0]+' ('+JOINT_GUIDES[active][1]+')') if joint else 'Your '+self.role+' · '+('reference pose' if self.step==2 else '3D preview'))
            if self.step==10:
                self.heading.setText('Setup complete · '+names[self.step])
            elif joint:
                self.heading.setText(f'{self.step+1} / 11 · joint {self.step-2} of 6 · '+names[self.step])
            else:
                self.heading.setText(f'{min(self.step+1,11)} / 11 · '+names[self.step])
            self.progress.setValue(self.step)
            self.progress.setVisible(self.step<10)
            self.back_button.setVisible(4<=self.step<=9)
            for widget in (self.role_box,self.ports,self.scan_button):widget.setVisible(self.step==0)
            self.support.setVisible(self.step==1);self.release.setVisible(self.step==1)
            self.reference_check.setVisible(self.step==2)
            self.direction.setVisible(joint);self.confirm.setVisible(joint)
            self.live.setVisible(self.step>=3)
            self.confirm.setChecked(False)
            if joint:
                n=JOINT_NAMES[self.step-3]
                self.direction.blockSignals(True);self.direction.setChecked(self.capture.directions[n]<0);self.direction.blockSignals(False)
                text=f'FIND IT · Motor {self.step-2}\n'+JOINT_GUIDES[n][2]+'\n\nTRY IT\nMove this joint slowly to each comfortable end of its travel. The highlighted 3D link should follow your hand. Stop at the mechanical limit; never force it.\n\nCHECK IT\nIf the 3D link moves the opposite way, use Reverse below. Confirm only after checking both ends and the direction.'
                self.next_button.setText('Confirm this joint and continue')
            elif self.step==0:
                text='For an assembled SO-101 with motor IDs 1–6 already assigned at 1 Mbps: connect one arm’s USB cable and motor power. Choose whether this is the follower (robot hand) or leader (hand-operated controller). If the port is unclear, unplug its USB cable, refresh, then reconnect and refresh. Connection reads registers only; it never enables motors.'
                self.next_button.setText('Connect and check six motors')
            elif self.step==1:
                text='The arm must be assembled with STS3215 motor IDs 1–6 at 1 Mbps. Support it before releasing torque. If a motor is missing, check power/cables and its ID; newly unconfigured motors must be assigned individually before calibration.'
                self.next_button.setText('Show the reference pose')
            elif self.step==2:
                text='Match the 3D reference on the right:\n1. Center the rotating base (1).\n2. Put the first long link upright using the low hinge (2).\n3. Put the next link approximately horizontal using the middle hinge (3).\n4. Straighten the hand (4), center its twist (5), and half-open the claw / trigger (6).\n\nThis is a stationary pose to copy. Green rings on the diagram show which real joint you are moving. Live 3D mirroring starts after you capture this reference. Hold still when you continue; this saves a backup and sets the homing offsets.'
                self.next_button.setText('Capture reference and begin calibration')
            elif self.step==9:
                text='All six joints are recorded. Review the travel and mirrored direction. Save writes the measured limits to the arm and exports LeRobot calibration plus its virtual binding. Motors remain off. The backup permits recovery if calibration is interrupted.'
                self.next_button.setText('Save calibration to arm and files')
            else:
                text='Calibration is saved and verified against the arm. Continue to hardware controls for measured live view. Motor enabling and held movement remain separate explicit actions. Repeat setup for the other arm.'
                self.next_button.setText('Finish and open live hardware controls')
            self.instructions.setText(text)
            self.instructions.setTextFormat(Qt.TextFormat.PlainText)
            if self.step in (0,1):
                self.instructions.setTextFormat(Qt.TextFormat.RichText)
                self.instructions.setText(text+'<br><br><a href="https://huggingface.co/docs/lerobot/so101">New motors? Follow the official wiring and individual motor-ID setup guide first.</a>')
                self.instructions.setOpenExternalLinks(True)

        def scan(self):
            if self.ticket is None:
                self.ticket=self.probe.start(());self.scan_button.setEnabled(False)
        def release_torque(self):
            if self.session and self.support.isChecked():self.session.stop(force=True)
            else:self.status.setText('Confirm that the arm is supported first.')
        def advance(self):
            if self.pending or self.closing:return
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
                    if not self.live.isChecked() or self.preview_step!=self.step or time.monotonic()-self.preview_at>1.:raise ValueError('Wait for this joint’s measured movement to appear in the viewport first.')
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

        def go_back(self):
            if not self.pending and 4<=self.step<=9:
                self.step-=1;self.confirm.setChecked(False);self.sequence=-1;self.preview_step=None;self.render_step()

        def require_sample(self):
            s=self.session.snapshot() if self.session else {};sample=s.get('sample')
            if not sample or s['stale'] or s['state'] not in ('read-only','calibrating'):
                raise ValueError('Wait for a fresh, complete connection to the six motors.')
            if any(m['torque'] for m in sample['motors'].values()):raise ValueError('Release motor torque before continuing.')
            return sample
        def reverse(self,checked):
            if self.capture and 3<=self.step<=8:
                self.capture.directions[JOINT_NAMES[self.step-3]]=-1 if checked else 1
                self.capture.confirmed.discard(JOINT_NAMES[self.step-3])
                self.confirm.setChecked(False);self.sequence=-1;self.preview_step=None;self.preview_generation+=1
        def live_changed(self,enabled):
            self.sequence=-1;self.preview_generation+=1;self.preview_step=None
            if not enabled:self.preview_status.setText('3D mirroring paused. Enable it to check this joint.')
            if not enabled and owner.worker and owner._ready:
                owner._command(lambda:owner.worker.release_hardware(self.role),owner._apply_status)
        def publish(self,positions,timestamp):
            if not owner._ready or self.preview_pending or self.closing:return
            # One queued update, even while RTX is busy. Read the newest complete
            # sample on execution rather than ageing a sample in the render queue.
            generation=self.preview_generation;issued_step=self.step;self.preview_pending=True
            selected=JOINT_NAMES[issued_step-3] if 3<=issued_step<=8 else None
            capture=self.capture
            def work():
                try:
                    if generation!=self.preview_generation or self.closing:return {'setup_cancelled':True}
                    current_positions,current_timestamp=positions,timestamp
                    if timestamp is not None:
                        snapshot=self.session.snapshot();sample=snapshot['sample']
                        if snapshot['stale'] or snapshot['state'] not in ('read-only','calibrating') or not sample:
                            raise ValueError('Telemetry is stale. Check USB and motor power before continuing.')
                        if any(m['torque'] for m in sample['motors'].values()):raise ValueError('Release motor torque before previewing calibration.')
                        current_positions=capture.preview(sample)[0];current_timestamp=sample['timestamp']
                    if selected!=self.selected_joint and hasattr(owner.worker,'select_joint') and selected:
                        owner.worker.select_joint(self.role,selected);self.selected_joint=selected
                    if timestamp is None and hasattr(owner.worker,'frame_selection'):
                        owner.worker.frame_selection(ROOTS[self.role])
                    return owner.worker.setup_pose(self.role,current_positions,current_timestamp)
                except Exception as exc:return {'setup_error':str(exc)}
            def done(frame):
                self.preview_pending=False
                if generation!=self.preview_generation:return
                if frame.get('setup_cancelled'):return
                if 'setup_error' in frame:
                    self.preview_error=frame['setup_error'];self.preview_status.setText(self.preview_error);self.preview_step=None
                    if timestamp is None:self.guide_shown=False
                else:
                    self.preview_error='';self.preview_at=time.monotonic()
                    owner._accept_frame(frame)
                    self.native_view.set_image(getattr(owner,'_image',None))
                    if timestamp is None:self.guide_ready=True
                    elif issued_step==self.step and not self.session.snapshot()['stale']:self.preview_step=issued_step
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
            self.last_raw=None;self.moved_at={};self.selected_joint=None;self.preview_error=''
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
            self.back_button.setEnabled(not self.pending)
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
                now=time.monotonic();raw={n:sample['motors'][i]['position'] for i,n in enumerate(JOINT_NAMES,1)}
                if self.last_raw:
                    for n in JOINT_NAMES:
                        if abs(raw[n]-self.last_raw[n])>=3:self.moved_at[n]=now
                self.last_raw=raw
                moving={n for n,t in self.moved_at.items() if now-t<.6}
                active=JOINT_NAMES[self.step-3] if 3<=self.step<=8 else None
                self.joint_map.set_state(active,moving,self.capture.confirmed if self.capture else ())
                if self.capture and 3<=self.step<=8:
                    n=JOINT_NAMES[self.step-3]
                    try:self.capture.observe(sample,n)
                    except ValueError as exc:self.status.setText(str(exc));self.next_button.setEnabled(False);return
                    low,high=self.capture.ranges[n]
                    self.travel.setValue(min(100,high-low))
                    self.travel.setFormat('Movement recorded' if high-low>=100 else 'Waiting for travel')
                    others=moving-{n}
                    self.movement.setText(('Movement detected: '+JOINT_GUIDES[n][0]) if n in moving else
                        ('You are moving '+', '.join(JOINT_GUIDES[x][0] for x in JOINT_NAMES if x in others)+'. Try joint '+str(self.step-2)+'.') if others else
                        'Waiting for movement of '+JOINT_GUIDES[n][0]+'.')
                    self.readings.setText(f'Motor {self.step-2} · {n.replace("_"," ")}\nEncoder now: {sample["motors"][self.step-2]["position"]}\nRecorded travel: {low} → {high} ({high-low} ticks)')
                elif self.capture:self.readings.setText('\n'.join(str(i)+' · '+JOINT_GUIDES[n][0]+': confirmed · '+str(self.capture.ranges[n][1]-self.capture.ranges[n][0])+' ticks' for i,n in enumerate(JOINT_NAMES,1)))
                else:self.readings.setText('\n'.join(f'Motor {i} · {JOINT_NAMES[i-1]} · encoder {m["position"]} · torque '+('ON' if m['torque'] else 'off') for i,m in sample['motors'].items()))
                if self.capture and self.live.isChecked() and sample['sequence']!=self.sequence:
                    positions,clipped=self.capture.preview(sample)
                    label='LIVE CALIBRATION PREVIEW · check reference and direction' if self.preview_step==self.step and now-self.preview_at<=1. else 'Waiting for a current 3D preview…'
                    self.preview_status.setText(self.preview_error or (label+('\nVirtual limits reached: '+', '.join(JOINT_GUIDES[n][0] for n in clipped) if clipped else '')))
                    if self.publish(positions,sample['timestamp']):self.sequence=sample['sequence']
                elif self.step==2 and not self.pending and not self.guide_shown:
                    self.preview_status.setText('REFERENCE GUIDE · copy this pose; green rings show real movement')
                    self.guide_shown=bool(self.publish(reference_pose(self.role),None))
                if not self.pending:self.connection.setText('Connected · motors remain off' if not any(m['torque'] for m in sample['motors'].values()) else 'Torque is ON. Support the arm and release torque.')
            elif s['stale']:
                self.preview_status.setText('Telemetry is stale. Mirroring stopped.');self.next_button.setEnabled(False);self.preview_step=None
        def shutdown(self):
            self.closing=True;self.live.setChecked(False);self.preview_generation+=1
            if self.session:self.session.stop(shutdown=True,force=False)
            else:self.timer.stop();self.shutdown_complete=True;self.done(0)
        def closeEvent(self,event):
            if self.transferred or self.shutdown_complete:event.accept();return
            event.ignore();self.shutdown()
        def reject(self):self.close()
    return SetupWizard()
