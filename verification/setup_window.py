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
                w.advance();state['phase']='reference'
            elif phase=='reference' and w.session.snapshot()['state']=='read-only' and not w.pending:
                assert not serial.writes
                w.support.setChecked(True);w.advance();state['phase']='guide'
            elif phase=='guide' and w.guide_ready:
                assert window.robot_panel.state.get('setup_roles')==['follower']
                window.grab().save(str(report.with_name('setup-reference.png')))
                w.grab().save(str(report.with_name('setup-wizard.png')))
                w.reference_check.setChecked(True);w.advance();state['phase']='range'
            elif phase=='range' and 3<=w.step<=8:
                i=w.step-2;n=list(w.capture.ranges)[i-1];low,high=w.capture.ranges[n]
                if low>1900:serial.registers[i][56:58]=(1900).to_bytes(2,'little')
                elif high<2200:
                    actual=panel.state.get('positions',{}).get('follower',{}).get(n)
                    expected=w.capture.preview(w.session.snapshot()['sample'])[0][n]
                    if actual is None or abs(actual-expected)>.01 or w.preview_step!=w.step:return
                    state['low_frames'][n]=bytes(w.native_view.image.constBits())
                    serial.registers[i][56:58]=(2200).to_bytes(2,'little')
                else:
                    # Wait for the native renderer to display the measured pose too.
                    actual=panel.state.get('positions',{}).get('follower',{}).get(n)
                    expected=w.capture.preview(w.session.snapshot()['sample'])[0][n]
                    if actual is None or abs(actual-expected)>.01:return
                    if w.preview_step!=w.step:return
                    assert w.native_view.image is not None
                    assert w.joint_map.active==n
                    assert bytes(w.native_view.image.constBits())!=state['low_frames'][n],n+' image did not change'
                    result['changed_joint_frames'].append(n)
                    if i==2:
                        w.grab().save(str(report.with_name('setup-joint.png')))
                        old_size=w.size();w.resize(960,640)
                        w.grab().save(str(report.with_name('setup-joint-compact.png')))
                        assert w.controls_scroll.widget().width()<=w.controls_scroll.viewport().width()
                        assert w.next_button.isVisible() and w.native_view.height()>=210
                        w.resize(old_size)
                    w.confirm.setChecked(True);w.advance()
                    result['mirrored_joints']=i
            elif phase=='range' and w.step==9:
                w.grab().save(str(report.with_name('setup-review.png')))
                w.advance();state['phase']='saved'
            elif phase=='saved' and w.step==10:
                assert (w.run_dir/'calibration.json').is_file() and (w.run_dir/'binding.json').is_file()
                assert not any(address==40 and value for _,address,value,_ in serial.writes)
                result.update(calibration_saved=True,torque_never_enabled=True,register_backup=True,
                    provisional_preview_label=bool(panel.state.get('setup_roles')))
                finish()
        except Exception as exc:finish(repr(exc))
    timer.timeout.connect(tick);timer.start(50)
