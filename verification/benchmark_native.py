"""Repeatable native performance matrix. Run only through native_guard.py."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import tempfile
import time

from profile_native import sample
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop/source'))
from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene


def summary(values):
    ordered=sorted(values)
    return {'count':len(values),'mean_ms':1000*statistics.mean(values),
            'p50_ms':1000*statistics.median(values),
            'p95_ms':1000*ordered[min(len(ordered)-1,math.ceil(.95*len(ordered))-1)],
            'p99_ms':1000*ordered[min(len(ordered)-1,math.ceil(.99*len(ordered))-1)],
            'max_ms':1000*max(values), 'throughput_fps':len(values)/sum(values)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--lifecycle-only',action='store_true')
    parser.add_argument('--reopen-count',type=int,default=3)
    args=parser.parse_args()
    report={'complete':False,'samples':[],'resolutions':[], 'lifecycle_only':args.lifecycle_only, 'reopen_count':args.reopen_count,
            'conditions':{'scene':'SO-101 leader and follower, default workspace',
                          'quality':'balanced','physics_hz':240,'substeps':4,
                          'cpu_quota_percent':200,'cache':'existing SDK shader/kernel caches'}}
    def save():args.report.write_text(json.dumps(report,indent=2)+'\n')
    def checkpoint(phase):
        entry=sample(phase);report['samples'].append(entry)
        if entry['gpu_memory_mib']:
            free=int(entry['gpu_memory_mib'].split(',')[1].strip())
            if free<4096:raise RuntimeError('GPU reserve below 4 GiB')
        save();print(phase,flush=True)
    worker=None
    try:
        checkpoint('before')
        with tempfile.TemporaryDirectory() as directory:
            scene=Path(directory)/'scene.usdc';create_default_scene(str(scene),include_robots=True)
            report['scene_sha256']=hashlib.sha256(scene.read_bytes()).hexdigest()
            profile=copy.deepcopy(DEFAULT_PROFILE)
            worker=SceneWorker(profile);worker.start()
            def call(fn):return worker.submit(fn).result(timeout=45)
            started=time.monotonic();call(lambda:worker.open_document(str(scene)))
            call(lambda:worker.tick(0));report['first_frame_seconds']=time.monotonic()-started
            for _ in range(5):call(lambda:worker.tick(0))
            checkpoint('first-frame')
            # Real wall-clock idle interval, preserving normal 30 Hz UI requests.
            started=time.monotonic();cpu=time.process_time();idle_count=0
            while time.monotonic()-started<10:
                if not call(lambda:worker.tick(.033)).get('unchanged'):raise AssertionError('Idle work resumed')
                idle_count+=1;time.sleep(1/30)
            report['idle']={'seconds':time.monotonic()-started,'process_cpu_seconds':time.process_time()-cpu,'ticks':idle_count}
            checkpoint('idle-10s')
            for width,height,seconds in ([] if args.lifecycle_only else [(640,360,20),(1280,720,120),(1920,1080,30)]):
                if worker.profile['rendering']['width']!=width:
                    candidate=copy.deepcopy(worker.profile);candidate['rendering'].update(width=width,height=height)
                    call(lambda:worker.configure(candidate,str(Path(directory)/'settings.json')))
                call(lambda:worker.command_robot('leader',{'shoulder_pan':.3,'wrist_roll':.2}))
                call(lambda:worker.set_playing(True))
                for _ in range(20):call(lambda:worker.tick(1/30))
                times=[];started=time.monotonic();last_sample=started;next_command=started+5;direction=-1
                while time.monotonic()-started<seconds:
                    begin=time.monotonic();call(lambda:worker.tick(1/30));times.append(time.monotonic()-begin)
                    now=time.monotonic()
                    if now>=next_command:
                        call(lambda:worker.command_robot('leader',{'shoulder_pan':direction*.3}));direction*=-1;next_command=now+5
                    if now-last_sample>=10:
                        checkpoint(f'{width}x{height}-{int(now-started)}s');last_sample=now
                report['resolutions'].append({'width':width,'height':height,'wall_seconds':time.monotonic()-started,
                    'mode':'uncapped throughput, fixed 1/30 s simulation per frame','frames':summary(times),
                    'raw_frame_seconds':times})
                call(lambda:worker.set_playing(False));checkpoint(f'{width}x{height}-complete')
            # Reset at default resolution; distinguish reset cost from first frame.
            candidate=copy.deepcopy(worker.profile);candidate['rendering'].update(width=1280,height=720)
            call(lambda:worker.configure(candidate,str(Path(directory)/'settings.json')))
            reset_times=[]
            for i in range(10):
                started=time.monotonic();call(worker.reset);reset_times.append(time.monotonic()-started)
                for _ in range(5):call(lambda:worker.tick(0))
                checkpoint('reset-'+str(i+1))
            report['reset']=summary(reset_times)
            reopen_times=[]
            for i in range(args.reopen_count):
                started=time.monotonic();call(lambda:worker.open_document(str(scene)));call(lambda:worker.tick(0));reopen_times.append(time.monotonic()-started)
                for _ in range(5):call(lambda:worker.tick(0))
                checkpoint('reopen-'+str(i+1))
            report['reopen_first_frame']=summary(reopen_times)
            report['complete']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error);raise
    finally:
        if worker:
            started=time.monotonic();worker.stop();report['shutdown_seconds']=time.monotonic()-started
        checkpoint('closed');save()


if __name__=='__main__':main()
