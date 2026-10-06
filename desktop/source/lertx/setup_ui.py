"""Guided SO-101 setup with torque-off calibration and visible measured preview."""
import copy,math,time
from pathlib import Path
from uuid import uuid4
from .devices import scan_result,RoleAssignments
from .transport import ConnectionProbe
from .hardware import HardwareSession
from .robot import JOINT_NAMES,ROOTS
from .setup_calibration import RangeCapture,JointSweep,reference_pose,save_json
from .hardware_calibration import save_binding
from .setup_visuals import JOINT_GUIDES,JointMap,SetupPreviewWindow
from .arm_colors import role_color,ROLE_NAMES

def build_setup_wizard(owner,session_factory=HardwareSession,scanner=None):
    from PySide6.QtCore import Qt,QTimer
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QProgressBar,QMessageBox,QWidget,QScrollArea,QColorDialog
    from .role_ui import widgets
    QLabel,QPushButton,QCheckBox=widgets(lambda: owner.profile)

    class SetupWizard(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.setWindowTitle('SO-101 · guided arm setup');self.resize(560,760);self.setModal(False)
            self.session=None;self.step=0;self.capture=None;self.candidate=None;self.role='follower'
            self.closing=False;self.shutdown_complete=False;self.transferred=False;self.pending=False
            self.guide_ready=False;self.preview_step=None;self.guide_shown=False;self.sequence=-1;self.preview_pending=False;self.preview_generation=0;self.observation=None
            self.preview_requested_at=0.;self.preview_at=0.;self.preview_error='';self.selected_joint=None
            self.sweep=None;self.auto_due=None;self.rendered_sequence=-1
            self.color_pending=False
            self.release_sequence=None
            self.back_target=None;self.back_stop=None
            self.preview_window=SetupPreviewWindow(owner)
            self.preview_window.navigation_parent=self
            self.native_view=self.preview_window.view;self.preview_title=self.preview_window.heading
            self.preview_status=self.preview_window.status
            self.probe=scanner or ConnectionProbe(scan_result);self.ticket=None;self.candidates=[]
            self.run_dir=Path(owner.config_path).parent/'calibration'/uuid4().hex
            outer=QVBoxLayout(self)
            title=QLabel('Meet your arm');title.setStyleSheet('font-size: 24px; font-weight: bold;');outer.addWidget(title)
            self.stage_label=QLabel('Connect  →  Prepare  →  Learn six joints  →  Save  →  Done');outer.addWidget(self.stage_label)
            self.identity=QLabel();self.identity.setWordWrap(True);outer.addWidget(self.identity)
            self.joint_map=JointMap();outer.addWidget(self.joint_map)
            body=QHBoxLayout();outer.addLayout(body,1)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setMinimumWidth(345)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.controls_scroll=scroll
            controls=QWidget();layout=QVBoxLayout(controls);scroll.setWidget(controls);body.addWidget(scroll,2)
            self.show_preview_button=QPushButton('Open live RTX 3D window');self.show_preview_button.clicked.connect(self.open_preview);layout.addWidget(self.show_preview_button)
            self.heading=QLabel();self.heading.setWordWrap(True);self.heading.setStyleSheet('font-size: 20px; font-weight: bold;');layout.addWidget(self.heading)
            self.progress=QProgressBar();self.progress.setRange(0,10);layout.addWidget(self.progress)
            self.instructions=QLabel();self.instructions.setWordWrap(True);layout.addWidget(self.instructions)
            self.movement=QLabel();self.movement.setWordWrap(True);outer.insertWidget(4,self.movement)
            self.travel=QProgressBar();self.travel.setRange(0,100);self.travel.setFormat('Waiting for travel');outer.insertWidget(5,self.travel)
            self.role_box=QComboBox();self.role_box.addItems(['follower','leader']);layout.addWidget(self.role_box)
            self.role_box.currentTextChanged.connect(self.change_role)
            self.color_button=QPushButton('Match printed-part color…');self.color_button.clicked.connect(self.choose_color);layout.addWidget(self.color_button)
            self.color_button.setToolTip('Choose a saved display color for this role before connecting. Both arms keep their text labels.')
            self.ports=QComboBox();self.ports.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.ports.setMinimumContentsLength(12);layout.addWidget(self.ports)
            self.scan_button=QPushButton('Refresh USB ports');self.scan_button.clicked.connect(self.scan);layout.addWidget(self.scan_button)
            self.support=QCheckBox('Arm supported; power switch within reach');layout.addWidget(self.support)
            self.release=QPushButton('Release torque for hand movement');self.release.clicked.connect(self.release_torque);layout.addWidget(self.release)
            self.release_result=QLabel();self.release_result.setWordWrap(True);layout.addWidget(self.release_result)
            self.reference_check=QCheckBox('My arm matches the reference pose');layout.addWidget(self.reference_check)
            self.direction=QCheckBox('Reverse this joint in the preview');self.direction.toggled.connect(self.reverse);layout.addWidget(self.direction)
            self.confirm=QCheckBox('Recorded travel and 3D directions match my arm');layout.addWidget(self.confirm)
            self.live=QCheckBox('Mirror my arm in 3D');self.live.setChecked(True);self.live.toggled.connect(self.live_changed);layout.addWidget(self.live)
            self.readings=QLabel();self.readings.setWordWrap(True);self.readings.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.readings)
            self.connection=QLabel();self.connection.setWordWrap(True);layout.addWidget(self.connection)
            self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.status)
            layout.addStretch(1)
            footer=QHBoxLayout();outer.addLayout(footer)
            self.cancel_button=QPushButton('Back to scene · cancel setup');self.cancel_button.clicked.connect(self.close);footer.addWidget(self.cancel_button)
            self.back_button=QPushButton('Back to previous joint');self.back_button.clicked.connect(self.go_back);footer.addWidget(self.back_button)
            footer.addStretch(1)
            self.next_button=QPushButton();self.next_button.setMinimumHeight(38);self.next_button.clicked.connect(self.advance);footer.addWidget(self.next_button)
            self.reset_button=QPushButton('Restart after connection fault');self.reset_button.clicked.connect(self.restart);layout.addWidget(self.reset_button);self.reset_button.hide()
            self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)
            self.render_step();self.scan()

        def render_step(self):
            self.cancel_button.setText("Back to scene" if self.step==10 else "Back to scene · cancel setup")
            self.status.clear()
            self.controls_scroll.verticalScrollBar().setValue(0)
            self.preview_step=None;self.preview_generation+=1;self.sequence=-1
            names=['Choose arm and USB port','Support the arm','Match the reference pose']+[JOINT_GUIDES[n][0] for n in JOINT_NAMES]+['Review all six joints','You are ready']
            joint=3<=self.step<=8
            active=JOINT_NAMES[self.step-3] if joint else None
            self.sweep=JointSweep(self.role,active) if joint else None;self.auto_due=None;self.rendered_sequence=-1
            self.sync_identity()
            self.preview_window.set_mode('reference' if self.step<=2 else 'waiting')
            if self.step<=2:self.guide_shown=False;self.guide_ready=False
            self.joint_map.set_state(active,confirmed=self.capture.confirmed if self.capture else ())
            self.travel.setVisible(joint);self.movement.setVisible(joint)
            self.movement.setText(self.sweep.prompt if self.sweep else '')
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
            self.back_button.setEnabled(not self.pending)
            self.back_button.setVisible(1<=self.step<=9)
            self.back_button.setText({1:'Back to arm selection',2:'Back to support check',3:'Back to reference pose'}.get(self.step,'Back to previous joint'))
            for widget in (self.role_box,self.ports,self.scan_button,self.color_button):widget.setVisible(self.step==0)
            self.support.setVisible(self.step==1);self.release.setVisible(self.step==1)
            self.release_result.setVisible(self.step==1)
            self.reference_check.setVisible(self.step==2)
            self.direction.setVisible(joint);self.confirm.setVisible(self.step==9)
            self.live.setVisible(self.step>=3)
            self.confirm.setChecked(False)
            if joint:
                n=JOINT_NAMES[self.step-3]
                self.direction.blockSignals(True);self.direction.setChecked(self.capture.directions[n]<0);self.direction.blockSignals(False)
                text=f'FIND IT · Motor {self.step-2}\n'+JOINT_GUIDES[n][2]+'\n\nMOVE, PAUSE, AND RETURN\nMove this joint to one comfortable end and pause briefly. Then move to the other end and pause. Finally return to the first end and pause. Never force the mechanism.\n\nOther joints can move naturally as you support the arm. Only this joint counts toward this step. Watch the solid arm in the RTX window; Reverse changes its direction if needed. The wizard continues automatically after a repeatable sweep.'
                self.next_button.setText('Waiting for the selected joint…');self.next_button.setEnabled(False)
            elif self.step==0:
                text='For an assembled SO-101 with motor IDs 1–6 already assigned at 1 Mbps: connect one arm’s USB cable and motor power. Choose whether this is the follower (robot hand) or leader (hand-operated controller). If the port is unclear, unplug its USB cable, refresh, then reconnect and refresh. Connection reads registers only; it never enables motors.'
                self.next_button.setText('Connect and check six motors')
            elif self.step==1:
                text='The arm must be assembled with STS3215 motor IDs 1–6 at 1 Mbps. Support it before releasing torque. If a motor is missing, check power/cables and its ID; newly unconfigured motors must be assigned individually before calibration.'
                self.next_button.setText('Show the reference pose')
            elif self.step==2:
                text='Match the solid arm in the RTX window:\n1. Center the rotating base (1).\n2. Put the first long link upright using the low hinge (2).\n3. Put the next link approximately horizontal using the middle hinge (3).\n4. Straighten the hand (4), center its twist (5), and half-open the claw / trigger (6).\n\nThis initial reference is a stationary pose to copy. Live 3D mirroring starts after you capture it. Hold still when you continue; this saves a backup and sets the homing offsets.'
                self.next_button.setText('Capture reference and begin calibration')
            elif self.step==9:
                text='All six joint sweeps were captured automatically. Move the whole arm and review its live 3D motion. Check that you explored each comfortable travel limit and the directions match. Use Back to repeat a joint if needed. Confirm below, then Save writes the recorded limits and exports calibration plus the virtual binding. Motors remain off.'
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

        def sync_identity(self):
            from .role_ui import role_icon
            color=role_color(owner.profile,self.role)
            for i in range(self.role_box.count()):
                self.role_box.setItemIcon(i,role_icon(self.role_box.itemText(i),owner.profile))
            self.setWindowIcon(role_icon(self.role,owner.profile))
            self.identity.setText('Setting up: '+ROLE_NAMES[self.role])
            self.identity.setStyleSheet(f'border-left: 12px solid {color}; padding: 8px; font-size: 16px; font-weight: bold;')
            self.setWindowTitle(self.role.capitalize()+' · guided SO-101 setup')
            self.preview_window.set_role(self.role)
            self.joint_map.role=self.role;self.joint_map.role_color=color;self.joint_map.update()

        def change_role(self,role):
            if self.step==0 and not self.session:
                previous=self.role
                if owner.worker and owner._ready:
                    owner._command(lambda:owner.worker.release_hardware(previous),owner._apply_status)
                self.role=role;self.render_step();self.select_assigned_port()

        def select_assigned_port(self):
            if self.session or self.step!=0:return
            try:
                roles=RoleAssignments(Path(owner.config_path).parent/'devices.json')
                state,candidate=roles.resolve(self.role,self.candidates)
                if state=='assigned':self.ports.setCurrentIndex(self.candidates.index(candidate))
            except (OSError,ValueError):pass

        def choose_color(self):
            from PySide6.QtGui import QColor
            color=QColorDialog.getColor(QColor(role_color(owner.profile,self.role)),self,
                'Printed-part color · '+self.role.capitalize())
            if color.isValid():self.apply_color(color.name())

        def apply_color(self,color):
            if self.session or self.color_pending or self.step!=0:return
            if not owner._ready or owner.worker is None:
                self.status.setText('Wait for the workspace to finish loading.');return
            if owner.devices.alive:
                self.status.setText('Close hardware sessions before changing arm colors.');return
            profile=copy.deepcopy(owner.profile);profile['general'][self.role+'_color']=color
            self.color_pending=True;self.role_box.setEnabled(False);self.color_button.setEnabled(False)
            self.status.setText('Applying printed-part color…')
            def work():
                try:
                    owner.worker.release_hardware(self.role)
                    return {'status':owner.worker.configure(profile,owner.config_path)}
                except Exception as exc:return {'error':str(exc)}
            def done(result):
                self.color_pending=False
                if 'error' not in result:
                    owner.profile=profile;owner.refresh_arm_colors();owner._apply_status(result['status'])
                if self.closing:return
                self.role_box.setEnabled(True);self.color_button.setEnabled(True)
                if 'error' in result:self.status.setText(result['error']);return
                self.guide_shown=False;self.guide_ready=False
                self.sync_identity();self.status.setText('Color saved for '+self.role+'. Choose the USB port to continue.')
            owner._command(work,done)

        def scan(self):
            if self.ticket is None:
                self.ticket=self.probe.start(());self.scan_button.setEnabled(False)
        def showEvent(self,event):
            super().showEvent(event)
            if not self.closing and not self.transferred:self.open_preview(activate=False)
        def open_preview(self,checked=False,*,activate=True):
            if self.preview_window.disposed:return
            self.preview_window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,self.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen))
            if not self.preview_window.isVisible():
                available=self.screen().availableGeometry()
                x=self.frameGeometry().right()+12
                if x+self.preview_window.width()>available.right():x=max(available.left(),available.right()-self.preview_window.width())
                self.preview_window.move(x,max(available.top(),self.y()))
            self.preview_window.show()
            if activate:self.preview_window.raise_();self.preview_window.activateWindow()
        def release_torque(self):
            if not self.support.isChecked():
                self.release_result.setText('Support the arm and check “Arm supported” before releasing torque.');return
            snapshot=self.session.snapshot() if self.session else {};sample=snapshot.get('sample')
            if not sample:
                self.release_result.setText('Release not confirmed — wait for the motor connection.');return
            self.release_sequence=sample['sequence'];self.release_request=self.session.stop(force=True)
            self.release_result.setText('Releasing torque… waiting for all six motors to confirm OFF.')
        def advance(self):
            if self.pending or self.color_pending or self.closing:return
            try:
                if self.step==0:
                    if not self.candidates:raise ValueError('No USB arm found. Connect USB and power, then refresh.')
                    self.candidate=self.candidates[self.ports.currentIndex()];self.role=self.role_box.currentText()
                    self.session=owner.devices.acquire(self.candidate,self.role,'setup',session_factory)
                    try:
                        roles=RoleAssignments(Path(owner.config_path).parent/'devices.json')
                        roles.assign(self.role,self.candidate,self.candidates)
                    except Exception:
                        self.session.stop(shutdown=True,force=False);self.session=None;raise
                    owner._hardware_windows['setup']=self
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
                    if not self.sweep.complete:raise ValueError(self.sweep.prompt)
                    if not self.preview_is_current():raise ValueError('Open the RTX window and wait for the current measured pose.')
                    n=JOINT_NAMES[self.step-3];self.capture.ranges[n]=self.sweep.bounds
                    self.capture.confirm(n);self.step+=1;self.render_step()
                elif self.step==9:
                    if not self.confirm.isChecked():raise ValueError('Review all recorded travel and 3D directions, then confirm before saving.')
                    self.require_sample();cal=self.capture.calibration();binding=self.capture.binding(self.session.device_id)
                    # Save pending artifacts before the hardware commit; never mark them accepted yet.
                    save_json(self.run_dir/'pending-calibration.json',cal.values)
                    save_binding(self.run_dir/'pending-binding.json',binding)
                    self.session.request('setup_save',cal);self.pending=True
                elif self.step==10:self.finish_setup()
            except Exception as exc:self.status.setText(str(exc))

        def preview_is_current(self):
            return (self.live.isChecked() and self.preview_window.isVisible() and self.preview_step==self.step
                and time.monotonic()-self.preview_at<=1. and self.sweep is not None and self.sweep.complete
                and self.rendered_sequence>=self.sweep.ready_sequence)

        def go_back(self):
            if self.pending:return
            if self.step==1:
                self.back_target=0;self.pending=True;self.session.stop(shutdown=True,force=False)
                self.status.setText('Returning to arm selection after device cleanup…')
            elif self.step==3:
                self.back_target=2;self.pending=True;self.back_stop=self.session.stop(force=False)
                self.status.setText('Restoring calibration registers before returning to the reference pose…')
            elif self.step==2 or 4<=self.step<=9:
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
                self.confirm.setChecked(False);self.sequence=-1;self.preview_step=None;self.preview_generation+=1;self.auto_due=None
        def live_changed(self,enabled):
            self.sequence=-1;self.preview_generation+=1;self.preview_step=None
            if not enabled:
                self.preview_status.setText('3D mirroring paused. Enable it to check this joint.')
                self.preview_window.set_mode('paused')
            if not enabled and owner.worker and owner._ready:
                owner._command(lambda:owner.worker.release_hardware(self.role),owner._apply_status)
        def publish(self,positions,timestamp):
            if not owner._ready or self.preview_pending or self.closing:return
            self.preview_requested_at=time.monotonic()
            # One queued update, even while RTX is busy. Read the newest complete
            # sample on execution rather than ageing a sample in the render queue.
            generation=self.preview_generation;issued_step=self.step;self.preview_pending=True;role=self.role
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
                        owner.worker.select_joint(role,selected);self.selected_joint=selected
                    if timestamp is None and hasattr(owner.worker,'frame_setup_arm'):
                        owner.worker.frame_setup_arm(role)
                    elif timestamp is None and hasattr(owner.worker,'frame_selection'):
                        owner.worker.frame_selection(ROOTS[role])
                    result=owner.worker.setup_pose(role,current_positions,current_timestamp)
                    return {**result,'setup_sequence':sample['sequence'] if timestamp is not None else -1}
                except Exception as exc:return {'setup_error':str(exc)}
            def done(frame):
                self.preview_pending=False
                if generation!=self.preview_generation:return
                if frame.get('setup_cancelled'):return
                if 'setup_error' in frame:
                    self.preview_window.set_mode('stale')
                    self.preview_error=frame['setup_error'];self.preview_status.setText(self.preview_error);self.preview_step=None
                    if timestamp is None:self.guide_shown=False
                else:
                    self.preview_window.set_mode('reference' if timestamp is None else 'live')
                    self.preview_error='';self.preview_at=time.monotonic()
                    owner._accept_frame(frame)
                    self.native_view.set_image(getattr(owner,'_image',None))
                    self.rendered_sequence=frame['setup_sequence']
                    if timestamp is None:self.guide_ready=True
                    elif issued_step==self.step and not self.session.snapshot()['stale']:self.preview_step=issued_step
            owner._command(work,done)
            return True
        def finish_setup(self):
            from .hardware_ui import build_hardware_panel
            panel=owner._hardware_windows.get(self.role)
            if panel is None or panel.closing or not panel.session.alive:
                panel=build_hardware_panel(owner,self.candidate,self.role)
            if hasattr(panel,'preview_window') and panel.preview_window is not self.preview_window:
                panel.preview_window.dispose()
            panel.calibration=self.capture.calibration();panel.binding=self.capture.binding(self.session.device_id)
            for n,spin in panel.targets.items():spin.setRange(*panel.calibration.limits(n))
            panel.calibration_label.setText('Wizard calibration verified · '+str(self.run_dir/'calibration.json'))
            panel.binding_label.setText('Verified reference and joint directions loaded')
            panel.preview_window=self.preview_window
            self.preview_window.navigation_parent=panel
            self.preview_window.back_button.setText("Back to hardware controls")
            self.preview_window.heading.setText(self.role.title()+' · live physical arm · NVIDIA RTX')
            self.preview_window.status.setText('Measured live view · motors remain off until explicitly enabled')
            show=QPushButton('Open live RTX 3D window');show.clicked.connect(self.preview_window.show);panel.layout().addWidget(show)
            owner._hardware_windows.pop('setup',None);owner._hardware_windows[self.role]=panel
            self.session.complete_setup()
            self.transferred=True;self.timer.stop();self.preview_generation+=1
            panel.live.setChecked(True);panel.show();self.done(1)
        def restart(self):
            if self.session and self.session.alive:
                self.session.stop(shutdown=True,force=False);self.status.setText('Closing the previous connection; click again when it has stopped.');return
            owner._hardware_windows.pop('setup',None)
            self.session=None;self.capture=None;self.step=0;self.pending=False
            self.selected_joint=None;self.preview_error='';self.sweep=None;self.auto_due=None
            self.native_view.set_image(None)
            self.guide_ready=False;self.preview_step=None;self.guide_shown=False;self.sequence=-1;self.preview_generation+=1
            self.reference_check.setChecked(False);self.support.setChecked(False);self.live.setChecked(True)
            self.run_dir=Path(owner.config_path).parent/'calibration'/uuid4().hex
            self.status.clear();self.connection.clear();self.preview_status.clear();self.readings.clear()
            self.reset_button.hide();self.render_step();self.scan()
        def poll(self):
            if self.step<=2 and not self.pending and not self.color_pending and not self.guide_shown and not self.closing:
                self.preview_status.setText('REFERENCE GUIDE · '+self.role+' · copy this pose, then capture to begin live motion')
                self.guide_shown=bool(self.publish(reference_pose(self.role),None))
            if self.ticket is not None:
                result=self.probe.poll(self.ticket)
                if result is not None:
                    self.ticket=None;self.scan_button.setEnabled(True);self.ports.clear()
                    self.candidates=result.get('candidates',[])
                    for c in self.candidates:self.ports.addItem(c.port+' · '+c.description+(' · '+c.serial if c.serial else ' · no unique serial'))
                    self.select_assigned_port()
                    self.status.setText('Choose the port for this arm.' if self.candidates else 'No USB ports found. Check the cable, motor power and USB driver, then refresh.')
            if not self.session:
                self.next_button.setEnabled(bool(self.candidates) and not self.color_pending);return
            self.session.heartbeat(False);s=self.session.snapshot();sample=s['sample'];setup=s.get('setup') or {}
            if self.back_target is not None:
                ready=not s['alive'] if self.back_target==0 else s['stop_completed']>=self.back_stop
                if ready:
                    target=self.back_target;self.back_target=None;self.pending=False
                    if setup.get('state')=='restore-unconfirmed' or s['stop_confirmed'] is False:
                        self.status.setText(s['error']);self.reset_button.show();return
                    if target==0:self.restart()
                    else:self.capture=None;self.step=target;self.reference_check.setChecked(False);self.render_step()
                return
            if self.step==1:
                from .hardware_feedback import torque_summary
                known=bool(sample and not s['stale']);on=known and any(m['torque'] for m in sample['motors'].values())
                self.release.setEnabled(bool(on) and self.release_sequence is None)
                self.release.setText('Releasing motors…' if self.release_sequence is not None else
                    'Release motors · move by hand' if on else
                    'Motors free — torque is off' if known else 'Torque unknown — waiting for motors')
                self.release.setToolTip('Calibration keeps motors off. Engagement becomes available after setup is complete.')
                if self.release_sequence is not None:
                    if s['stop_confirmed'] is False or s['state']=='fault':
                        self.release_result.setText('Release unconfirmed: '+s['error']);self.release_sequence=None
                    elif s['stop_completed']>=self.release_request and sample and not s['stale'] and sample['sequence']>self.release_sequence and s['stop_confirmed'] is True and not any(m['torque'] for m in sample['motors'].values()):
                        self.release_result.setText('Released and verified · all 6 motors are OFF. Already-off motors will not visibly change.');self.release_sequence=None
                elif not self.release_result.text() or self.release_result.text().startswith('Torque '):
                    self.release_result.setText(torque_summary(s)+' Calibration keeps torque off.')
            if self.closing:
                if not s['alive']:
                    self.timer.stop();self.shutdown_complete=True
                    if setup.get('state')=='restore-unconfirmed' or s['stop_confirmed'] is False:
                        QMessageBox.critical(self,'Setup recovery required',s['error']+'\nBackup: '+str(self.run_dir/'original-registers.json'))
                    self.done(0)
                return
            self.next_button.setEnabled(not self.pending and bool(sample) and not s['stale'])
            if self.step==2:self.next_button.setEnabled(not self.pending and bool(sample) and not s['stale'] and self.guide_ready)
            if 3<=self.step<=8:self.next_button.setEnabled(False)
            self.back_button.setEnabled(not self.pending)
            if s['state']=='fault':
                self.pending=False;self.status.setText(s['error']);self.next_button.setEnabled(False);self.reset_button.show()
                if self.live.isChecked():self.live.setChecked(False)
                return
            if self.step==1 and s['state']=='read-only':self.pending=False
            if self.step==2 and setup.get('state')=='recording':
                self.capture=RangeCapture(self.role,setup['homings'],setup.get('reference_positions'));self.pending=False;self.step=3;self.render_step()
            if self.step==9 and setup.get('state')=='saved':
                try:
                    save_json(self.run_dir/'calibration.json',self.capture.calibration().values)
                    save_binding(self.run_dir/'binding.json',self.capture.binding(self.session.device_id))
                    save_json(self.run_dir/'setup.json',dict(schema=1,role=self.role,device_id=self.session.device_id,calibration_id=self.capture.calibration().identity))
                    self.pending=False;self.step=10;self.render_step()
                except Exception as exc:self.status.setText('Calibration is on the arm but saving files failed: '+str(exc));return
            if sample and not s['stale']:
                now=time.monotonic()
                active=JOINT_NAMES[self.step-3] if 3<=self.step<=8 else None
                self.joint_map.set_state(active,confirmed=self.capture.confirmed if self.capture else ())
                if self.capture and 3<=self.step<=8:
                    n=JOINT_NAMES[self.step-3]
                    try:
                        self.capture.observe(sample,n)
                        self.sweep.observe(sample)
                    except ValueError as exc:self.status.setText(str(exc));self.next_button.setEnabled(False);return
                    low,high=self.capture.ranges[n]
                    self.travel.setValue(self.sweep.progress)
                    self.travel.setFormat('Sweep captured' if self.sweep.complete else f'Hold {self.sweep.phase+1} of 3 · %p%')
                    self.movement.setText(self.sweep.feedback(sample))
                    if self.sweep.complete:
                        if self.preview_is_current() and not self.pending:
                            if self.auto_due is None:self.auto_due=now+.6
                            self.next_button.setText('Joint captured — continuing…')
                            if now>=self.auto_due:self.advance();return
                        else:self.auto_due=None
                    self.readings.setText(f'Motor {self.step-2} · {n.replace("_"," ")}\nEncoder now: {sample["motors"][self.step-2]["position"]}\nRecorded travel: {low} → {high} ({high-low} ticks)')
                elif self.capture:self.readings.setText('\n'.join(str(i)+' · '+JOINT_GUIDES[n][0]+': confirmed · '+str(self.capture.ranges[n][1]-self.capture.ranges[n][0])+' ticks' for i,n in enumerate(JOINT_NAMES,1)))
                else:self.readings.setText('\n'.join(f'Motor {i} · {JOINT_NAMES[i-1]} · encoder {m["position"]} · torque '+('ON' if m['torque'] else 'off') for i,m in sample['motors'].items()))
                if (self.capture and self.live.isChecked() and sample['sequence']!=self.sequence
                        and (self.sequence==-1 or now-self.preview_requested_at >=
                        1/getattr(owner,'_debug_target_fps',owner.profile['rendering']['target_fps']))):
                    positions,clipped=self.capture.preview(sample)
                    label='LIVE CALIBRATION PREVIEW · check reference and direction' if self.preview_step==self.step and now-self.preview_at<=1. else 'Waiting for a current 3D preview…'
                    self.preview_status.setText(self.preview_error or (label+('\nVirtual limits reached: '+', '.join(JOINT_GUIDES[n][0] for n in clipped) if clipped else '')))
                    if self.publish(positions,sample['timestamp']):self.sequence=sample['sequence']
                elif self.step==2 and not self.pending and not self.guide_shown:
                    self.preview_status.setText('REFERENCE GUIDE · copy this pose, then capture to begin live motion')
                    self.guide_shown=bool(self.publish(reference_pose(self.role),None))
                if not self.pending:self.connection.setText('Connected · motors remain off' if not any(m['torque'] for m in sample['motors'].values()) else 'Torque is ON. Support the arm and release torque.')
            elif s['stale']:
                self.preview_window.set_mode('stale')
                self.preview_status.setText('Telemetry is stale. Mirroring stopped.');self.next_button.setEnabled(False);self.preview_step=None
                self.auto_due=None
                if self.sweep:self.sweep.reset_hold()
        def shutdown(self):
            self.closing=True;self.live.setChecked(False);self.preview_generation+=1
            self.preview_window.dispose()
            if self.session:self.session.stop(shutdown=True,force=False)
            else:self.timer.stop();self.shutdown_complete=True;self.done(0)
        def closeEvent(self,event):
            if self.transferred or self.shutdown_complete:event.accept();return
            event.ignore();self.shutdown()
        def reject(self):self.close()
    return SetupWizard()
