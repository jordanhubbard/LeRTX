"""User-facing recording, presets and explicit physical follower motion."""
import time
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QFileDialog,QMessageBox,QScrollArea,QWidget
from .robot_session import RobotSession,load_recording
from .devices import RoleAssignments,scan_result
from .transport import ConnectionProbe
from .robot_poses import list_presets,load_pose
from .robot import JOINT_NAMES,ROLES,joint_limits
from .setup_visuals import SetupPreviewPanel
from .role_ui import widgets


def build_robot_session_panel(owner):
    Label,Button,Check=widgets(lambda:owner.profile)

    class SessionPanel(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.setWindowTitle('Robot session · record, follow and replay');self.resize(1300,800)
            self.session=RobotSession(owner.devices,owner.config_path)
            self.session_assignments={}
            self.scan=ConnectionProbe(scan_result);self.ticket=None;self.loaded=None
            self.preview_pending=False;self.preview_generation=0;self.preview_play=False;self.preview_started=0.
            self.closed=False
            outer=QHBoxLayout(self);left=QVBoxLayout();outer.addLayout(left,2)
            scroll=QScrollArea();scroll.setWidgetResizable(True)
            content=QWidget();controls=QVBoxLayout(content);scroll.setWidget(content);left.addWidget(scroll,1)
            controls.addWidget(Label('<b>Robot session</b>'))
            text=Label('Record measured joints with motors off, preview saved sequences, or explicitly start follower motion. The leader stays free. Stop releases follower motors.');text.setWordWrap(True);controls.addWidget(text)
            self.roles=QComboBox();self.roles.addItems(['Leader and follower','Leader only','Follower only']);controls.addWidget(self.roles)
            self.connect_button=Button('Connect assigned arms');self.connect_button.clicked.connect(self.connect_arms);controls.addWidget(self.connect_button)
            self.disconnect_button=Button('Disconnect session');self.disconnect_button.clicked.connect(self.disconnect);controls.addWidget(self.disconnect_button)
            self.device_status=Label();self.device_status.setWordWrap(True);controls.addWidget(self.device_status)
            self.record_button=Button('Start joint recording');self.record_button.clicked.connect(self.toggle_recording);controls.addWidget(self.record_button)
            row=QHBoxLayout();controls.addLayout(row)
            save=Button('Save sequence…');save.clicked.connect(self.save_sequence);row.addWidget(save)
            discard=Button('Discard recording');discard.clicked.connect(self.discard_recording);row.addWidget(discard)
            load=Button('Open sequence…');load.clicked.connect(self.open_sequence);controls.addWidget(load)
            self.record_status=Label('No recording');self.record_status.setWordWrap(True);controls.addWidget(self.record_status)
            row=QHBoxLayout();controls.addLayout(row)
            simulate=Button('Preview sequence in RTX');simulate.clicked.connect(self.preview_sequence);row.addWidget(simulate)
            playback=Button('Play sequence on follower');playback.clicked.connect(lambda:self.start_motion('playback'));row.addWidget(playback)
            follow=Button('Start follower following leader');follow.clicked.connect(lambda:self.start_motion('follow'));controls.addWidget(follow)
            controls.addWidget(Label('<b>Robot action profiles · saved poses</b>'))
            self.presets=QComboBox();controls.addWidget(self.presets)
            for name,path,builtin in list_presets(owner.config_path):self.presets.addItem(name,str(path))
            row=QHBoxLayout();controls.addLayout(row)
            preview=Button('Preview pose in RTX');preview.clicked.connect(self.preview_pose);row.addWidget(preview)
            run=Button('Run pose on follower');run.clicked.connect(lambda:self.start_motion('pose'));row.addWidget(run)
            self.live=Check('Show measured leader and follower in RTX');self.live.setChecked(True);self.live.toggled.connect(self.live_changed);controls.addWidget(self.live)
            self.stop_button=Button('STOP · release follower motors');self.stop_button.setMinimumHeight(48)
            self.stop_button.clicked.connect(self.stop);left.addWidget(self.stop_button)
            self.status=Label();self.status.setWordWrap(True);left.addWidget(self.status);controls.addStretch(1)
            back=Button('Back to Device Manager');back.clicked.connect(self.back);left.addWidget(back)
            self.preview=SetupPreviewPanel(owner);self.preview.back_button.hide();self.preview.set_role('follower');outer.addWidget(self.preview,3)
            self.preview.identity.setText('Robot session · Leader and Follower')
            self.preview.legend.hide();self.preview.set_mode('paused')
            self.preview.status.setText('Connect assigned arms for measured motion, or preview a saved pose or sequence.')
            self.preview.view.empty_message='Connect arms or preview a pose to display the RTX scene.'
            self.preview.view.set_image(getattr(owner,'_image',None))
            self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(50)

        def selected_roles(self):return ROLES if self.roles.currentIndex()==0 else ('leader',) if self.roles.currentIndex()==1 else ('follower',)

        def connect_arms(self):
            if self.ticket is not None:return
            self.ticket=self.scan.start(());self.status.setText('Discovering assigned robot arms…')

        def disconnect(self):
            self.stop();self.live.setChecked(False);self.session.close();self.session_assignments.clear();self.status.setText('Session disconnected; any recording is retained. Reassign session-only arms in Devices before reconnecting.')

        def toggle_recording(self):
            try:
                if self.session.recording:self.session.stop_recording()
                else:self.session.start_recording(self.selected_roles())
            except (ValueError,OSError) as exc:self.status.setText(str(exc))

        def save_sequence(self):
            self.session.stop_recording()
            path,_=QFileDialog.getSaveFileName(self,'Save joint sequence',str(Path(owner.config_path).parent/'sequence.json'),'LeRTX sequence (*.json)')
            if path:
                try:self.session.save_recording(path);self.loaded=load_recording(path);self.status.setText('Sequence saved: '+path)
                except (ValueError,OSError) as exc:self.status.setText(str(exc))

        def discard_recording(self):
            if self.session.recording:self.status.setText('Stop recording before discarding it.');return
            if not self.session.unsaved or QMessageBox.question(self,'Discard recording?','Discard the unsaved joint sequence?')==QMessageBox.StandardButton.Yes:
                self.session.discard_recording()

        def open_sequence(self):
            path,_=QFileDialog.getOpenFileName(self,'Open joint sequence','','LeRTX sequence (*.json)')
            if path:
                try:self.loaded=load_recording(path);self.status.setText('Loaded sequence: '+path)
                except (ValueError,OSError) as exc:self.status.setText(str(exc))

        def start_motion(self,mode):
            if self.session.mode!='idle':self.status.setText('Stop current motion first.');return
            if QMessageBox.question(self,'Start physical follower motion?',
                'The follower will engage and move at bounded speed. Support the arm, clear its workspace and keep the power switch accessible. The leader stays free. Start now?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            try:
                pose=load_pose(self.presets.currentData()) if mode=='pose' else None
                self.session.start_motion(mode,recording=self.loaded,pose=pose)
                self.preview_play=False;self.live.setChecked(True);self.status.setText('Engaging follower motors…')
            except (ValueError,OSError,TypeError) as exc:self.status.setText(str(exc))

        def stop(self):
            self.session.stop_motion('Motion stopped; follower release requested.')
            self.preview_play=False;self.preview_generation+=1
            self.status.setText(self.session.error)

        def live_changed(self,enabled):
            self.preview_generation+=1
            if not enabled and owner._ready:
                for role in self.session.accesses:
                    owner._command(lambda r=role:owner.worker.release_hardware(r),owner._apply_status)

        def publish(self,positions,physical=False):
            if self.preview_pending or not owner._ready:return
            self.preview_pending=True;generation=self.preview_generation
            def perform():
                if self.closed or generation!=self.preview_generation:return None
                result=None
                for role,values in positions.items():
                    if physical:
                        # Re-read just before native publication, not when queued.
                        values=self.session.positions(role);sample=self.session.accesses[role].snapshot()['sample']
                        result=owner.worker.hardware_pose(role,values,sample['timestamp'])
                    else:
                        # Exact, paused reconstruction; setting simulation targets
                        # alone cannot move a paused scene.
                        result=owner.worker.setup_pose(role,values)
                        owner.worker.release_hardware(role)
                return result if physical else owner.worker.tick(0.)
            def work():
                try:return perform()
                except Exception as exc:return {'session_preview_error':str(exc)}
            def done(result):
                self.preview_pending=False
                if result and not self.closed and generation==self.preview_generation:
                    if 'session_preview_error' in result:self.preview.status.setText(result['session_preview_error'])
                    else:owner._accept_frame(result)
            owner._command(work,done)

        def preview_pose(self):
            if self.session.mode!='idle':self.status.setText('Stop physical motion before simulation preview.');return
            try:
                pose=load_pose(self.presets.currentData());self.live.setChecked(False);self.preview_play=False
                self.publish({r:{n:joint_limits(r)[n][0]+v*(joint_limits(r)[n][1]-joint_limits(r)[n][0]) for n,v in values.items()} for r,values in pose.items()})
                self.preview.set_mode('simulation');self.status.setText('Simulation pose preview · '+self.presets.currentText())
            except (ValueError,OSError) as exc:self.status.setText(str(exc))

        def preview_sequence(self):
            if not self.loaded:self.status.setText('Open or save a sequence first.');return
            if self.session.mode!='idle':self.status.setText('Stop physical motion before previewing a sequence.');return
            self.live.setChecked(False);self.preview_play=True;self.preview_started=time.monotonic()
            self.preview.set_mode('simulation');self.status.setText('Playing sequence in simulation; no motor commands.')

        def poll(self):
            if self.closed:return
            if self.ticket is not None:
                result=self.scan.poll(self.ticket)
                if result is not None:
                    self.ticket=None
                    try:
                        if result.get('state')!='success':raise ValueError('USB discovery failed; check Devices.')
                        roles=RoleAssignments(Path(owner.config_path).parent/'devices.json');selected={}
                        roles.session=dict(self.session_assignments);roles.update(result['candidates']);self.session_assignments=dict(roles.session)
                        for role in self.selected_roles():
                            state,candidate=roles.resolve(role,result['candidates'])
                            if state!='assigned':raise ValueError('Assign '+role+' in Device Manager first.')
                            selected[role]=candidate
                        self.session.connect(selected)
                    except (ValueError,OSError) as exc:self.status.setText(str(exc))
            self.session.tick(active_window=self.isActiveWindow())
            states=self.session.snapshots()
            self.connect_button.setEnabled(not states and self.ticket is None)
            self.disconnect_button.setEnabled(bool(states))
            self.roles.setEnabled(not states)
            self.device_status.setText('\n'.join(r.title()+': '+s['state']+(' · '+s['error'] if s['error'] else '') for r,s in states.items()) or 'No arms connected')
            self.record_button.setText('Stop joint recording' if self.session.recording else 'Start joint recording')
            frames=len(self.session.record['frames']) if self.session.record else 0
            self.record_status.setText(f'{frames} frames'+(' · RECORDING' if self.session.recording else ' · unsaved' if self.session.unsaved else ''))
            if self.session.error:self.status.setText(self.session.error)
            elif self.session.mode!='idle':self.status.setText('Physical follower: '+self.session.mode+(' · limited to measured travel: '+', '.join(self.session.limited) if self.session.limited else ''))
            try:
                if self.preview_play:
                    elapsed=time.monotonic()-self.preview_started
                    frame=next((f for f in reversed(self.loaded['frames']) if f['t']<=elapsed),self.loaded['frames'][0])
                    positions={}
                    from .joint_binding import JointBinding
                    for role,values in frame['roles'].items():
                        joints=[JointBinding(**j) for j in self.loaded['devices'][role]['binding']['joints']]
                        positions[role]={j.name:j.convert(max(min(j.observed),min(max(j.observed),values[j.name]))) for j in joints}
                    self.publish(positions)
                    if elapsed>=self.loaded['frames'][-1]['t']:self.preview_play=False;self.status.setText('Simulation playback complete.')
                elif self.live.isChecked() and states:
                    positions={r:self.session.positions(r) for r in states}
                    self.publish(positions,physical=True);self.preview.set_mode('live')
            except (ValueError,KeyError) as exc:
                self.preview.set_mode('stale')
                if self.session.mode=='idle':self.preview.status.setText(str(exc))

        def back(self):
            if self.close():QTimer.singleShot(0,owner._on_devices)

        def reject(self):
            self.close()

        def closeEvent(self,event):
            self.stop()
            if self.session.unsaved and QMessageBox.question(self,'Unsaved joint recording','Discard the unsaved joint recording and close?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                event.ignore();return
            self.live.setChecked(False);self.closed=True;self.timer.stop()
            if self.ticket is not None:self.scan.cancel(self.ticket)
            self.session.close();self.preview.dispose();event.accept()

    return SessionPanel()
