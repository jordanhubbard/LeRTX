"""Real Qt-window timing and idle measurement; native_guard.py is required."""
import argparse
import copy
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

from profile_native import sample
from benchmark_native import summary
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop/source'))
from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene
from lertx.ui import build_application,build_main_window


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    from PySide6.QtCore import QTimer
    result={'complete':False,'samples':[sample('before')],'resolution':[1280,720], 'target_fps':30}
    app=build_application([])
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'pair.usdc';create_default_scene(str(path),include_robots=True)
        profile=copy.deepcopy(DEFAULT_PROFILE)
        window=build_main_window(profile,lambda:SceneWorker(profile),str(path),str(Path(directory)/'settings.json'))
        window.show();started=time.monotonic();window.open_scene(str(path))
        state={'phase':'startup','since':started,'frames':[],'heartbeat':[],'last_beat':started}
        original=window._accept_frame
        def accept(value):
            original(value)
            if state['phase']=='playing' and not value.get('unchanged'):state['frames'].append(time.monotonic())
        window._accept_frame=accept
        timer=QTimer(window)
        def finish(error=None):
            timer.stop()
            if error:result['error']=error
            else:result['complete']=True
            result['screenshot_saved']=window.grab().save(str(args.report.with_suffix('.png')))
            window.close()
        def tick():
            now=time.monotonic()
            if now-started>80:finish('Qt benchmark deadline exceeded');return
            if state['phase']=='startup' and window._image is not None:
                result['first_frame_seconds']=now-started;state.update(phase='settling',since=now)
            elif state['phase']=='settling' and window._idle_frame:
                state.update(phase='idle',since=now,cpu=time.process_time())
                result['samples'].append(sample('idle-start'))
            elif state['phase']=='idle' and now-state['since']>=5:
                result['idle']={'wall_seconds':now-state['since'],'process_cpu_seconds':time.process_time()-state['cpu']}
                result['samples'].append(sample('idle-end'))
                state.update(phase='playing',since=time.monotonic(),sim_start=window.clock.sim_time,last_beat=time.monotonic())
                window.play_button.click()
            elif state['phase']=='playing':
                state['heartbeat'].append(now-state['last_beat']);state['last_beat']=now
                if now-state['since']>=20:
                    frames=state['frames'];duration=now-state['since']
                    result['playing']={'wall_seconds':duration,'frames':len(frames),'display_fps':len(frames)/duration,
                        'simulation_seconds':window.clock.sim_time-state['sim_start'],
                        'simulation_to_wall_ratio':(window.clock.sim_time-state['sim_start'])/duration,
                        'frame_intervals':summary([b-a for a,b in zip(frames,frames[1:])]) if len(frames)>1 else None,
                        'qt_heartbeat_intervals':summary(state['heartbeat'])}
                    result['samples'].append(sample('playing-end'))
                    window.play_button.click();state.update(phase='pausing',since=now)
            elif state['phase']=='pausing' and window._idle_frame:
                result['samples'].append(sample('paused'))
                finish()
        timer.timeout.connect(tick);timer.start(20)
        try:app.exec()
        finally:
            if window.worker:window.worker.stop()
            result['samples'].append(sample('closed'))
            args.report.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
