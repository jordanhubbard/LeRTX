"""Exercise native picking and Qt joint dragging in an already contained window."""
import json
import math
import time
from pathlib import Path


def attach(window, report):
    from PySide6.QtCore import QTimer, QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    report = Path(report)
    timer = QTimer(window)
    started = time.monotonic()
    state = {'phase':'startup'}
    result = {'complete':False}

    def finish(error=None):
        timer.stop()
        result.update(complete=error is None, seconds=round(time.monotonic()-started,2))
        if error: result['error']=str(error)
        window.grab().save(str(report.with_suffix('.png')))
        report.write_text(json.dumps(result,indent=2)+'\n')

    def pointer(kind, x, y):
        button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
        point=QPointF(x,y)
        QApplication.sendEvent(window.viewport_label,QMouseEvent(kind,point,point,button,buttons,Qt.KeyboardModifier.NoModifier))

    def picked(value):
        if not value: raise AssertionError('No robot joint found with native picking')
        state.update(phase='drag',hit=value)
        u,v,joint=value
        result['joint']=joint
        left,top,width,height=window.viewport_label.image_rect()
        x,y=left+u*width,top+v*height
        pointer(QEvent.Type.MouseButtonPress,x,y)
        # Release before the native pick returns, deliberately exercising latency.
        pointer(QEvent.Type.MouseMove,x+60,y)
        pointer(QEvent.Type.MouseButtonRelease,x+60,y)

    def verify():
        joint=state['hit'][2];role,name=joint['role'],joint['name']
        physics=window.worker.physics
        target=physics.targets[role][name]
        measured=physics.robot_positions()[role][name]
        expected=max(joint['low'],min(joint['high'],joint['value']+math.radians(30)))
        assert abs(target-expected)<1e-6,(target,expected)
        assert abs(measured-joint['value'])>.005,(measured,joint['value'])
        assert not window.worker.clock.playing
        try:window.worker.drag_joint('follower','shoulder_pan',.1)
        except ValueError:pass
        else:raise AssertionError('Following follower accepted a drag')
        assert window.worker.document.dirty is False
        window.worker.clock.play()
        start_time=window.worker.clock.sim_time
        for _ in range(8):
            frame=window.worker.drag_joint(role,name,target-.2,elapsed=1/30)
        assert window.worker.clock.sim_time>start_time+.2
        playing_measured=window.worker.physics.robot_positions()[role][name]
        assert abs(playing_measured-measured)>.03
        window.worker.clock.pause()
        frame=window.worker.tick(0.)
        return dict(target=target,measured=measured,paused=True,follower_locked=True,
            playing_drag_measured=playing_measured,playing_drag_advances_physics=True,
            authored_scene_unchanged=True,final_frame=frame)

    def verified(value):
        joint=state['hit'][2]
        assert abs(window.robot_panel.inputs[joint['name']].value()-30)<.2, 'Target readout did not follow drag'
        window._accept_frame(value.pop('final_frame'))
        window.robot_panel.show_target(joint['role'],joint['name'],value['target']-.2)
        result.update(value)
        assert window._selected_path(), 'Viewport selection did not reach hierarchy'
        result['selected_path']=window._selected_path()
        finish()

    def tick():
        try:
            if time.monotonic()-started>240:finish('Interaction test deadline exceeded');return
            if state['phase']=='startup' and window._image is not None and window._idle_frame and not window._pending:
                image=window._image
                state['before']=image.copy()
                candidates=[]
                for y in range(8,image.height(),14):
                    for x in range(8,image.width(),14):
                        color=image.pixelColor(x,y)
                        if color.green()>color.red()*1.25 and color.green()>60:
                            candidates.append((x/image.width(),y/image.height()))
                def probe():
                    for u,v in candidates:
                        hit=window.worker.pick(u,v)
                        joint=hit['joint']
                        if joint and joint['role']=='leader' and joint['name']!='gripper':return u,v,joint
                    return None
                state['phase']='picking';window._command(probe,picked)
            elif state['phase']=='drag' and window.viewport_label.press is None and not window._pending and window._idle_frame:
                state['phase']='verifying';window._command(verify,verified)
            if 'Native: ' in window.native_status_label.text() and 'Error:' in window.native_status_label.text():
                finish(window.native_status_label.text())
        except Exception as error:
            finish(repr(error))
    timer.timeout.connect(tick);timer.start(40)
    return timer
