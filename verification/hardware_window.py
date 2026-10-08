"""Bounded native live-pose and selected-joint UI regression, without physical I/O."""
import json
import math
import time
from pathlib import Path


def attach(window,report):
    from PySide6.QtCore import QTimer
    report=Path(report);timer=QTimer(window);started=time.monotonic();phase={'name':'startup'}
    result={'complete':False,'physical_hardware_tested':False}
    def finish(error=None):
        timer.stop();result.update(complete=error is None,seconds=round(time.monotonic()-started,2))
        if error:result['error']=str(error)
        window.grab().save(str(report.with_suffix('.png')))
        report.write_text(json.dumps(result,indent=2)+'\n')
    def native():
        worker=window.worker
        from lertx.robot import home_positions
        positions=home_positions('leader');positions['shoulder_lift']=.35
        before=worker.tick(0)['frame']
        frame=worker.hardware_pose('leader',positions,time.monotonic())
        actual=frame['robots']['positions']['leader']
        for name,value in positions.items():assert abs(actual[name]-value)<.001,(name,actual[name],value)
        assert frame['robots']['live_roles']==['leader'] and not frame['playing']
        assert before.data!=frame['frame'].data
        for operation in (lambda:worker.set_playing(True),lambda:worker.drag_joint('follower','shoulder_pan',.1),lambda:worker.reset(),lambda:worker.hardware_pose('leader',positions,time.monotonic()-1)):
            try:operation()
            except ValueError:pass
            else:raise AssertionError('Live ownership or stale-data guard failed')
        assert not worker.document.dirty
        worker.release_hardware('leader')
        return worker.reset()
    def restored(status):
        window._apply_status(status)
        path='/World/Leader/Geometry/base_link/shoulder_link/upper_arm_link'
        window.tree.setCurrentItem(window._tree_items[path]);phase['name']='selection'
        result.update(live_pose_fk=True,live_render_changed=True,simulation_ownership=True,stale_pose_rejected=True,authored_usd_unchanged=True)
    def measured(value):
        result.update(value);finish()
    def tick():
        try:
            if time.monotonic()-started>120:finish('Native interaction deadline exceeded');return
            if phase['name']=='startup' and window._image is not None and window._idle_frame and not window._pending:
                phase['name']='native';window._command(native,restored)
            elif phase['name']=='selection' and not window._pending:
                panel=window.robot_panel
                slider=panel.sliders['leader','shoulder_lift']
                low,high=panel._range['leader','shoulder_lift']
                assert slider.isEnabled()
                slider.setValue(round(1000*(math.radians(20)-low)/(high-low)))
                phase['name']='slider'
            elif phase['name']=='slider' and not window._pending and window._idle_frame and window.viewport_label.intent is None:
                phase['name']='verify'
                def check():
                    worker=window.worker
                    actual=worker.physics.robot_positions()['leader']['shoulder_lift']
                    target=worker.physics.targets['leader']['shoulder_lift']
                    assert abs(target-math.radians(20))<.004,(actual,target)
                    assert abs(actual-target)<.08,(actual,target)
                    assert not worker.clock.playing
                    return dict(selected_joint_slider=True,target_radians=target,measured_radians=actual,paused=True)
                window._command(check,measured)
        except Exception as exc:finish(repr(exc))
    timer.timeout.connect(tick);timer.start(50)
