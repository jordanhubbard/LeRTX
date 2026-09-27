"""Short native resource profile; invoke only through native_guard.py."""
import argparse
import copy
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop/source'))
from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from lertx.scene import create_default_scene


def sample(label):
    data={'phase':label,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    data['rss_kib']=int(fields['VmRSS'].split()[0])
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split(':',2)[2].lstrip('/')
    for name in ('memory.current','memory.peak','memory.max','memory.swap.current'):
        data[name]=(cg/name).read_text().strip()
    result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
    data['gpu_memory_mib']=result.stdout.strip()
    return data


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    report={'samples':[sample('before')],'completed':False}
    profile=copy.deepcopy(DEFAULT_PROFILE);profile['rendering'].update(width=640,height=360)
    worker=SceneWorker(profile)
    def call(fn):return worker.submit(fn).result(timeout=45)
    try:
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pair.usdc';create_default_scene(str(path),include_robots=True)
            worker.start();start=time.monotonic()
            call(lambda:worker.open_document(str(path)))
            report['samples'].append(sample('opened'))
            call(lambda:worker.tick(0));report['first_frame_seconds']=time.monotonic()-start
            for _ in range(4):call(lambda:worker.tick(0))
            report['samples'].append(sample('settled'))
            start=time.monotonic()
            for _ in range(100):
                if not call(lambda:worker.tick(.02)).get('unchanged'):raise AssertionError('Idle native work was not suppressed')
            report['idle_100_ticks_seconds']=time.monotonic()-start
            report['samples'].append(sample('idle'))
            call(lambda:worker.command_robot('leader',{'shoulder_pan':.3}))
            call(lambda:worker.set_playing(True));times=[]
            for _ in range(20):
                start=time.monotonic();call(lambda:worker.tick(1/30));times.append(time.monotonic()-start)
            report['frame_seconds']={'mean':sum(times)/len(times),'maximum':max(times)}
            report['samples'].append(sample('playing'))
            for i in range(2):
                call(worker.reset)
                for _ in range(5):call(lambda:worker.tick(0))
                report['samples'].append(sample('reset-'+str(i+1)))
            report['completed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        try:worker.stop()
        finally:
            report['samples'].append(sample('closed'))
            args.report.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
