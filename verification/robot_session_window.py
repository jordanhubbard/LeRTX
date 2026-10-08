"""Native RTX preset regression; caller supplies an isolated profile and GPU owner."""
import json,time
from pathlib import Path


def attach(window,report):
    from PySide6.QtCore import QTimer
    import numpy as np
    from lertx.robot import joint_limits
    from lertx.robot_poses import load_pose
    report=Path(report);timer=QTimer(window);started=time.monotonic()
    state={'phase':0};result={'complete':False,'physical_motors_commanded':False}

    def finish(error=None):
        timer.stop();result.update(complete=error is None,error=error)
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        panel=state.get('panel')
        if panel:panel.grab().save(str(report.with_suffix('.png')));panel.close()
        window.has_unsaved_changes=False;window.close()

    def verify_pose(panel):
        pose=load_pose(panel.presets.currentData())
        measured=window.robot_panel.state['positions']
        for role,values in pose.items():
            for name,value in values.items():
                low,high=joint_limits(role)[name]
                assert abs(measured[role][name]-(low+value*(high-low)))<.001,(role,name)

    def tick():
        try:
            if time.monotonic()-started>100:finish('Native session deadline exceeded');return
            if not window._ready or window._pending or window._image is None:return
            if state['phase']==0:
                window.open_robot_session();panel=window._robot_session_window
                state['panel']=panel;panel.presets.setCurrentIndex(0);panel.preview_pose();state['phase']=1
            elif state['phase']==1:
                panel=state['panel']
                if panel.preview_pending:return
                verify_pose(panel);state['first']=window._image.copy()
                panel.presets.setCurrentIndex(1);panel.preview_pose();state['phase']=2
            else:
                panel=state['panel']
                if panel.preview_pending:return
                verify_pose(panel)
                a=np.frombuffer(state['first'].constBits(),dtype=np.uint8).reshape(-1,4).astype(int)
                b=np.frombuffer(window._image.constBits(),dtype=np.uint8).reshape(-1,4).astype(int)
                ratio=float(np.mean(np.max(np.abs(a[:,:3]-b[:,:3]),axis=1)>20))
                result['fraction_pixels_changed_above_20_levels']=ratio
                assert ratio>.005,('Pose changed but meshes remained visually stale',ratio)
                assert panel.preview.view.image==window._image
                assert not window.devices.active_controllers()
                result.update(poses_match=True,integrated_preview_matches=True)
                finish()
        except Exception as exc:finish(repr(exc))
    timer.timeout.connect(tick);timer.start(100)
