"""Native Qt guided setup regression. Caller supplies resource containment."""
import json,math,time
from pathlib import Path


def attach(window,report):
    from PySide6.QtCore import QTimer
    from lertx.devices import Candidate
    from lertx.hardware import HardwareSession
    from lertx.setup_ui import build_setup_wizard
    from lertx.transport import ConnectionProbe
    from lertx.usb_bus import FeetechBus
    from tests.test_setup import CalibrationSerial
    report=Path(report);timer=QTimer(window);started=time.monotonic()
    # Emulated identities and calibration files must never enter the operator profile.
    window.config_path=str(report.parent/'setup-test-profile'/'settings.json')
    state={'phase':'startup'};result={'complete':False,'physical_hardware_tested':False}
    serial=CalibrationSerial()
    def finish(error=None):
        timer.stop();result.update(complete=error is None,seconds=round(time.monotonic()-started,2))
        if error:
            result.update(error=str(error),phase=state['phase'])
            wizard=state.get('wizard')
            if wizard:
                result.update(wizard_step=wizard.step,wizard_status=wizard.status.text(),
                    preview_status=wizard.preview_status.text())
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
            phase=state['phase'];panel=window.robot_panel;w=state.get('wizard')
            progress=(phase,w.step if w else None)
            if progress!=state.get('last_progress'):
                print('Guided setup phase:',progress,flush=True);state['last_progress']=progress
            # Live calibration continuously queues measured poses. Waiting for
            # an empty viewport queue here can starve the wizard controls.
            if not window._ready or (window._pending and phase in ('startup','moved')):return
            if phase=='startup' and window._image is not None and window._idle_frame:
                slider=panel.sliders['leader','shoulder_lift']
                low,high=panel._range['leader','shoulder_lift']
                assert slider.isEnabled()
                slider.setValue(round(1000*(.35-low)/(high-low)));state['phase']='moved'
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
                state.update(wizard=w,phase='connect');w.move(window.x()+20,window.y()+100);w.show()
            elif phase=='connect' and w.candidates:
                w.advance();state['phase']='reference'
            elif phase=='reference' and w.session.snapshot()['state']=='read-only' and not w.pending:
                assert not serial.writes
                w.support.setChecked(True);w.advance();state['phase']='guide'
            elif phase=='guide' and w.guide_ready:
                assert window.robot_panel.state.get('setup_roles')==['follower']
                window.screen().grabWindow(0).save(str(report.with_name('setup-reference.png')))
                w.grab().save(str(report.with_name('setup-wizard.png')))
                w.reference_check.setChecked(True);w.advance();state['phase']='range'
            elif phase=='range' and 3<=w.step<=8:
                i=w.step-2;n=list(w.capture.ranges)[i-1];low,high=w.capture.ranges[n]
                if low>1900:serial.registers[i][56:58]=(1900).to_bytes(2,'little')
                elif high<2200:serial.registers[i][56:58]=(2200).to_bytes(2,'little')
                else:
                    # Wait for the native renderer to display the measured pose too.
                    actual=panel.state.get('positions',{}).get('follower',{}).get(n)
                    expected=w.capture.preview(w.session.snapshot()['sample'])[0][n]
                    if actual is None or abs(actual-expected)>.01:return
                    w.confirm.setChecked(True);w.advance()
                    result['mirrored_joints']=i
            elif phase=='range' and w.step==9:
                window.grab().save(str(report.with_name('setup-review.png')))
                w.advance();state['phase']='saved'
            elif phase=='saved' and w.step==10:
                assert (w.run_dir/'calibration.json').is_file() and (w.run_dir/'binding.json').is_file()
                assert not any(address==40 and value for _,address,value,_ in serial.writes)
                result.update(calibration_saved=True,torque_never_enabled=True,register_backup=True,
                    provisional_preview_label=bool(panel.state.get('setup_roles')))
                finish()
        except Exception as exc:finish(repr(exc))
    timer.timeout.connect(tick);timer.start(50)
