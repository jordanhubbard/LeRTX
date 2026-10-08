"""Visible Windows follower-unlock regression on the existing native owner."""
import json, math, time
from pathlib import Path

def attach(window, report):
    from PySide6.QtCore import QTimer
    report=Path(report);timer=QTimer(window);started=time.monotonic();phase='startup'
    baseline=None
    def finish(error=None):
        timer.stop()
        result={'complete':error is None,'seconds':round(time.monotonic()-started,2),
            'physical_hardware_tested':False,'provider_request_sent':False}
        if error:result['error']=str(error)
        else:result.update(follower_unlocked=True,slider_moved_articulation=True,paused=True,
            actual_radians=window.robot_panel.state['positions']['follower']['shoulder_lift'])
        window.grab().save(str(report.with_suffix('.png')))
        report.write_text(json.dumps(result,indent=2)+'\n')
    def tick():
        nonlocal phase,baseline
        try:
            if time.monotonic()-started>90:finish('Interaction deadline exceeded');return
            if window._pending or not window._ready:return
            panel=window.robot_panel
            if phase=='startup' and window._image is not None and window._idle_frame:
                window.tree.setCurrentItem(window._tree_items['/World/Follower/Geometry/base_link/shoulder_link/upper_arm_link'])
                phase='selected'
            elif phase=='selected':
                assert not panel.sliders['follower','shoulder_lift'].isEnabled()
                assert panel.follow.isChecked() and panel.follow.isEnabled()
                panel.follow.setChecked(False);phase='unlocked'
            elif phase=='unlocked' and not panel.state['following']:
                slider=panel.sliders['follower','shoulder_lift']
                assert slider.isEnabled() and not panel.follow.isChecked()
                baseline=window._image.copy()
                low,high=panel._range['follower','shoulder_lift']
                slider.setValue(round(1000*(.35-low)/(high-low)))
                phase='moved'
            elif phase=='moved' and window.viewport_label.intent is None and window._idle_frame:
                actual=panel.state['positions']['follower']['shoulder_lift']
                assert abs(actual-.35)<.08,actual
                assert window._image!=baseline
                assert not window.clock.playing
                finish()
        except Exception as error:finish(repr(error))
    timer.timeout.connect(tick);timer.start(50)
