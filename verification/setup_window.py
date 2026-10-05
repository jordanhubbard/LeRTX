"""Native Windows/Qt guided setup regression. Caller supplies resource containment."""
import json,math,time
from pathlib import Path


def attach(window,report):
    from PySide6.QtCore import Qt,QTimer
    from lertx.devices import Candidate
    from lertx.hardware import HardwareSession
    from lertx.setup_ui import build_setup_wizard
    from lertx.transport import ConnectionProbe
    from lertx.usb_bus import FeetechBus
    from tests.test_setup import CalibrationSerial
    report=Path(report);timer=QTimer(window);started=time.monotonic()
    # Emulated identities and calibration files must never enter the operator profile.
    window.config_path=str(report.parent/'setup-test-profile'/'settings.json')
    state={'phase':'startup','low_frames':{}};result={'complete':False,'physical_hardware_tested':False,'changed_joint_frames':[]}
    serial=CalibrationSerial()
    def finish(error=None):
        timer.stop();result.update(complete=error is None,seconds=round(time.monotonic()-started,2))
        if error:
            result['error']=str(error)
            result['phase']=state['phase']
            result['native_status']=window.native_status_label.text()
            result['ui_status']=window.statusBar().currentMessage()
        window.grab().save(str(report.with_suffix('.png')))
        report.write_text(json.dumps(result,indent=2)+'\n')
        if state.get('wizard'):state['wizard'].shutdown()
        QTimer.singleShot(500,window.close)
    def factory(candidate,role):
        return HardwareSession(candidate,role,verify=lambda c:None,
            bus_factory=lambda port:FeetechBus(port,serial_factory=lambda **kwargs:serial))
    def tick():
        try:
            if time.monotonic()-started>120:finish('Native setup deadline exceeded');return
            if not window._ready:return
            phase=state['phase'];panel=window.robot_panel;w=state.get('wizard')
            if window._pending and phase in ('startup','moved','verifying','wizard'):return
            if phase=='startup' and window._image is not None and window._idle_frame:
                low,high=panel._range['leader','shoulder_lift']
                panel.sliders['leader','shoulder_lift'].setValue(round(1000*(.35-low)/(high-low)));state['phase']='moved'
            elif phase=='moved' and window._idle_frame and window.viewport_label.intent is None:
                def verify():
                    q=window.worker.physics.robot_positions()['leader']['shoulder_lift']
                    assert abs(q-.35)<.08,q
                    assert not window.worker.clock.playing
                    return q
                def checked(q):result.update(named_joint_slider=True,paused_kinematics=True,measured_radians=q);state['phase']='wizard'
                state['phase']='verifying';window._command(verify,checked)
            elif phase=='wizard':
                w=build_setup_wizard(window,factory,ConnectionProbe(lambda **k:{'state':'success','candidates':[Candidate('native-setup-emulator',1,2,'native-test')]}))
                w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,window.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen))
                state.update(wizard=w,phase='connect');w.move(window.x()+20,window.y()+100);w.show()
            elif phase=='connect' and w.candidates:
                w.role_box.setCurrentText('leader')
                assert 'Leader' in w.identity.text() and '#1FAD9E' in w.identity.styleSheet()
                w.role_box.setCurrentText('follower')
                w.apply_color('#8050d0');state['phase']='color'
            elif phase=='color' and not w.color_pending and not window._pending:
                from lertx.config import load_profile
                assert load_profile(window.config_path)['general']['follower_color']=='#8050d0'
                assert '#8050d0' in w.identity.styleSheet()
                assert 'Follower (selected)' in w.preview_window.legend.text()
                def colors():
                    from pxr import Usd,UsdShade
                    from lertx.arm_colors import apply_material_colors
                    # Inspect the exact USD snapshot loaded into the native renderer.
                    runtime=Usd.Stage.Open(str(window.worker.runtime_file))
                    shaders=[UsdShade.Shader(p) for p in runtime.Traverse()
                        if str(p.GetPath()).startswith('/World/Follower/') and '3d_printed' in str(p.GetPath()) and p.IsA(UsdShade.Shader)]
                    assert shaders
                    actual=[tuple(s.GetInput('diffuseColor').Get()) for s in shaders if s.GetInput('diffuseColor')]
                    assert actual and all(c[2]>c[0]>c[1] for c in actual),actual
                    return len(actual)
                def colored(count):
                    result.update(custom_color_materials=count,role_identity=True,color_persistence=True)
                    state['phase']='colored'
                state['phase']='checking-color';window._command(colors,colored)
            elif phase=='colored':
                w.advance();state['phase']='reference'
            elif phase=='reference' and w.session.snapshot()['state']=='read-only' and not w.pending:
                assert not serial.writes
                w.support.setChecked(True);w.advance();state['phase']='guide'
            elif phase=='guide' and w.guide_ready:
                assert window.robot_panel.state.get('setup_roles')==['follower']
                w.preview_window.grab().save(str(report.with_name('setup-reference.png')))
                w.grab().save(str(report.with_name('setup-wizard.png')))
                w.reference_check.setChecked(True);w.advance();state['phase']='range'
            elif phase=='range' and 3<=w.step<=8:
                i=w.step-2;n=list(w.capture.ranges)[i-1]
                if w.sweep.start is None:return
                if w.sweep.phase==0:serial.registers[i][56:58]=(1600).to_bytes(2,'little')
                elif w.sweep.phase==1:
                    actual=panel.state.get('positions',{}).get('follower',{}).get(n)
                    expected=w.capture.preview(w.session.snapshot()['sample'])[0][n]
                    if actual is None or abs(actual-expected)>.01 or w.preview_step!=w.step:return
                    if n not in state['low_frames']:state['low_frames'][n]=bytes(w.native_view.image.constBits())
                    serial.registers[i][56:58]=(2500).to_bytes(2,'little')
                elif w.sweep.phase==2 and n not in result['changed_joint_frames']:
                    # Wait for the native renderer to display the measured pose too.
                    actual=panel.state.get('positions',{}).get('follower',{}).get(n)
                    expected=w.capture.preview(w.session.snapshot()['sample'])[0][n]
                    if actual is None or abs(actual-expected)>.01:return
                    if w.preview_step!=w.step:return
                    assert w.native_view.image is not None
                    assert w.joint_map.active==n
                    assert w.preview_window.isVisible() and w.preview_window.isWindow()
                    assert bytes(w.native_view.image.constBits())!=state['low_frames'][n],n+' image did not change'
                    result['changed_joint_frames'].append(n)
                    if i==2:
                        w.grab().save(str(report.with_name('setup-joint.png')))
                        w.preview_window.grab().save(str(report.with_name('setup-live-rtx.png')))
                        old_size=w.size();w.resize(560,640)
                        w.grab().save(str(report.with_name('setup-joint-compact.png')))
                        assert w.controls_scroll.widget().width()<=w.controls_scroll.viewport().width()
                        assert w.next_button.isVisible() and w.native_view.height()>=210
                        w.resize(old_size)
                    serial.registers[i][56:58]=(1600).to_bytes(2,'little')
                    result['mirrored_joints']=i
            elif phase=='range' and w.step==9:
                assert len(w.capture.confirmed)==6 and len(result['changed_joint_frames'])==6
                result['automatic_joint_advancement']=True
                w.grab().save(str(report.with_name('setup-review.png')))
                w.confirm.setChecked(True);w.advance();state['phase']='saved'
            elif phase=='saved' and w.step==10:
                assert (w.run_dir/'calibration.json').is_file() and (w.run_dir/'binding.json').is_file()
                assert not any(address==40 and value for _,address,value,_ in serial.writes)
                result.update(calibration_saved=True,torque_never_enabled=True,register_backup=True,
                    provisional_preview_label=bool(panel.state.get('setup_roles')))
                finish()
        except Exception as exc:finish(repr(exc))
    timer.timeout.connect(tick);timer.start(50)
