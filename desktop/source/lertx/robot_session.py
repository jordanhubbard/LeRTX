"""Bounded joint recordings and calibrated physical robot session coordination."""
import copy,json,math,time
from pathlib import Path
from .robot import JOINT_NAMES,ROLES,joint_limits,follower_targets
from .hardware_calibration import Calibration,load_binding,binding_targets
from .setup_calibration import save_json

MAX_FRAMES=72000


def load_saved_setup(config_path,role,device_id):
    root=Path(config_path).parent/'calibration'
    runs=sorted(root.glob('*/setup.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    for path in runs:
        try:metadata=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        if isinstance(metadata,dict) and metadata.get('role')==role and metadata.get('device_id')==device_id:
            calibration=Calibration.load(path.with_name('calibration.json'))
            if metadata.get('calibration_id')!=calibration.identity:raise ValueError('Saved calibration identity does not match its completion record')
            return calibration,load_binding(path.with_name('binding.json'),role,device_id,calibration)
    raise ValueError('No saved calibration and binding for '+role+'. Calibrate this device first.')


def validate_recording(data):
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('kind')!='lertx-joint-sequence':
        raise ValueError('Not a LeRTX joint sequence')
    devices=data.get('devices');frames=data.get('frames')
    if not isinstance(devices,dict) or not devices or set(devices)-set(ROLES):raise ValueError('Invalid sequence roles')
    calibrations={}
    for role,meta in devices.items():
        if not isinstance(meta,dict) or not isinstance(meta.get('device_id'),str) or not meta['device_id']:raise ValueError('Missing sequence device identity')
        calibration=Calibration(meta.get('calibration'))
        if meta.get('calibration_id')!=calibration.identity:raise ValueError('Sequence calibration identity mismatch')
        from .joint_binding import RobotBinding,JointBinding
        raw=meta.get('binding')
        if not isinstance(raw,dict):raise ValueError('Missing sequence joint binding')
        try:binding=RobotBinding(raw['role'],raw['device_id'],raw['calibration_id'],tuple(JointBinding(**j) for j in raw['joints']))
        except (KeyError,TypeError,AttributeError) as exc:raise ValueError('Invalid sequence joint binding') from exc
        if binding.role!=role or binding.device_id!=meta['device_id'] or binding.calibration_id!=calibration.identity:raise ValueError('Sequence binding identity mismatch')
        for joint in binding.joints:
            if joint.unit!=('percent' if joint.name=='gripper' else 'degrees'):raise ValueError('Invalid hardware observation units')
            for value in joint.observed:calibration.encode(joint.name,value)
        calibrations[role]=calibration
    if not isinstance(frames,list) or not 1<=len(frames)<=MAX_FRAMES:raise ValueError('Sequence must contain 1–72000 frames')
    previous=-1.
    for frame in frames:
        t=frame.get('t') if isinstance(frame,dict) else None
        if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t<0 or not previous<t<=3600:raise ValueError('Invalid sequence timestamps')
        previous=t
        if not isinstance(frame.get('roles'),dict) or set(frame['roles'])!=set(devices):raise ValueError('Sequence frame roles differ')
        for role,values in frame['roles'].items():
            if not isinstance(values,dict) or set(values)!=set(JOINT_NAMES):raise ValueError('Incomplete sequence joints')
            calibration=calibrations[role]
            for name,value in values.items():calibration.encode(name,value)
    return data


def load_recording(path):
    path=Path(path)
    if path.stat().st_size>64*1024*1024:raise ValueError('Sequence file exceeds 64 MiB')
    try:return validate_recording(json.loads(path.read_text(encoding='utf-8')))
    except RecursionError as exc:raise ValueError('Sequence file nesting is too deep') from exc


class RobotSession:
    """Qt polls this object; only HardwareSession workers touch serial devices."""
    def __init__(self,registry,config_path,clock=time.monotonic):
        self.registry=registry;self.config_path=config_path;self.clock=clock
        self.accesses={};self.loading=set();self.error='';self.mode='idle';self.pending_mode=None
        self.recording=False;self.record=None;self.unsaved=False;self.record_roles=()
        self.loaded=None;self.play_index=0;self.started=0.;self.last_record_sequences=None
        self.fixed_targets=None;self.limited=[];self.record_started=0.

    def connect(self,candidates):
        if self.accesses:raise ValueError('Disconnect the current robot session first.')
        try:
            for role,candidate in candidates.items():
                access=self.registry.acquire(candidate,role,'session');self.accesses[role]=access
                access.request('connect')
        except Exception:
            self.close();raise
        self.error=''

    def snapshots(self):return {r:a.snapshot() for r,a in self.accesses.items()}

    def ready(self,role,allow_arming=False):
        access=self.accesses.get(role)
        if not access:raise ValueError('Connect '+role+' first.')
        s=access.snapshot();sample=s['sample']
        if not access.writable or s['state'] not in (('read-only','armed','arming') if allow_arming else ('read-only','armed')) or s['stale'] or not sample:
            raise ValueError(role+': fresh telemetry and session control are required.')
        if sample['calibration_error'] or not sample['observations'] or not access.controller.calibration or not access.controller.binding:
            raise ValueError(role+': matching calibration and binding are required.')
        return access,s

    def positions(self,role):
        access,s=self.ready(role);c=access.controller
        mapped=c.binding.map_observation({n+'.pos':v for n,v in s['sample']['observations'].items()},
            device_id=access.device_id,calibration_id=c.calibration.identity,captured_at=s['sample']['timestamp'],now=self.clock())
        return {path.rsplit('/',1)[-1]:v for path,v in mapped.items()}

    def start_recording(self,roles):
        if self.unsaved:raise ValueError('Save or discard the previous recording first.')
        devices={}
        for role in roles:
            access,s=self.ready(role);c=access.controller
            from dataclasses import asdict
            devices[role]=dict(device_id=access.device_id,calibration_id=c.calibration.identity,
                calibration=c.calibration.values,binding=asdict(c.binding))
        if not devices:raise ValueError('Select a connected arm to record.')
        self.record=dict(schema=1,kind='lertx-joint-sequence',devices=devices,frames=[],units='joint degrees; gripper percent')
        self.record_roles=tuple(roles);self.record_started=self.clock();self.last_record_sequences=None
        self.recording=True;self.error=''

    def stop_recording(self):self.recording=False

    def save_recording(self,path):
        if self.recording:raise ValueError('Stop recording before saving.')
        validate_recording(self.record);save_json(path,self.record);self.unsaved=False

    def discard_recording(self):
        if self.recording:raise ValueError('Stop recording first.')
        self.record=None;self.unsaved=False

    def start_motion(self,mode,*,recording=None,pose=None):
        if self.mode!='idle':raise ValueError('Stop current motion first.')
        follower,s=self.ready('follower')
        if any(m['torque'] for m in s['sample']['motors'].values()):raise ValueError('Release follower motors before starting this session.')
        if mode=='follow':
            _,leader=self.ready('leader')
            if any(m['torque'] for m in leader['sample']['motors'].values()):raise ValueError('Leader must remain free, with torque off.')
            self.follow_targets()
        elif mode=='playback':
            data=validate_recording(recording)
            meta=data['devices'].get('follower')
            if not meta or meta['device_id']!=follower.device_id or meta['calibration_id']!=follower.controller.calibration.identity:
                raise ValueError('Physical playback requires this follower and its current calibration.')
            self.loaded=copy.deepcopy(data);self.play_index=0
            previous=dict(s['sample']['observations']);previous_t=0.;timeline=[];elapsed=0.
            calibration=follower.controller.calibration
            for frame in self.loaded['frames']:
                target=frame['roles']['follower']
                travel=max(abs(calibration.encode(n,target[n])-calibration.encode(n,previous[n])) for n in JOINT_NAMES)
                elapsed+=max(frame['t']-previous_t,travel/follower.controller.session.SPEED,.05)
                timeline.append(dict(t=elapsed,roles=frame['roles']))
                previous=target;previous_t=frame['t']
            self.play_start=dict(s['sample']['observations']);self.play_frames=timeline
        elif mode=='pose':
            positions={n:joint_limits('follower')[n][0]+v*(joint_limits('follower')[n][1]-joint_limits('follower')[n][0]) for n,v in pose['follower'].items()}
            self.fixed_targets=self.qualified_targets(positions)
        else:raise ValueError('Unknown motion mode')
        follower.request('arm');self.mode='arming';self.pending_mode=mode;self.started=self.clock();self.error=''

    def qualified_targets(self,positions):
        binding=self.accesses['follower'].controller.binding;clamped={};self.limited=[]
        for j in binding.joints:
            value=positions[j.name];low,high=sorted(j.radians)
            clamped[j.name]=max(low,min(high,value))
            if abs(clamped[j.name]-value)>1e-6:self.limited.append(j.name)
        return binding_targets(binding,clamped)

    def follow_targets(self):return self.qualified_targets(follower_targets(self.positions('leader')))

    def stop_motion(self,reason=''):
        active=self.mode!='idle';self.mode='idle';self.pending_mode=None
        if active and 'follower' in self.accesses:
            access=self.accesses['follower']
            if access.writable:access.stop(force=True)
        if reason:self.error=reason

    def tick(self,active_window=True):
        for role,access in list(self.accesses.items()):
            if role!='follower' or self.mode=='idle':access.heartbeat(False)
            s=access.snapshot()
            if s['state']=='read-only' and role not in self.loading:
                try:
                    c=access.controller
                    if c.calibration is None or c.binding is None:c.calibration,c.binding=load_saved_setup(self.config_path,role,access.device_id)
                    access.request('calibration',c.calibration);self.loading.add(role)
                except (ValueError,OSError) as exc:self.error=str(exc);self.loading.add(role)
        try:
            if self.recording:
                samples={r:self.ready(r)[1]['sample'] for r in self.record_roles}
                sequences=tuple(samples[r]['sequence'] for r in self.record_roles)
                elapsed=self.clock()-self.record_started
                if elapsed>3600 or len(self.record['frames'])>=MAX_FRAMES:self.recording=False;self.error='Recording limit reached; save the captured sequence.'
                elif sequences!=self.last_record_sequences:
                    self.record['frames'].append(dict(t=elapsed,roles={r:dict(s['observations']) for r,s in samples.items()},
                        samples={r:dict(sequence=s['sequence'],timestamp=s['timestamp']) for r,s in samples.items()}))
                    self.last_record_sequences=sequences;self.unsaved=True
            if self.mode!='idle':
                if not active_window:raise ValueError('Motion stopped: robot session lost focus. Start explicitly to resume.')
                follower,s=self.ready('follower',allow_arming=self.mode=='arming')
                if self.mode=='arming':
                    if s['state']=='armed' and all(m['torque'] for m in s['sample']['motors'].values()):
                        self.mode=self.pending_mode;self.started=self.clock()
                    elif self.clock()-self.started>5:raise ValueError('Follower engagement did not complete.')
                    else:follower.heartbeat(False);return
                if s['state']!='armed':raise ValueError('Follower is no longer armed.')
                if self.mode=='follow':
                    _,leader=self.ready('leader')
                    if any(m['torque'] for m in leader['sample']['motors'].values()):raise ValueError('Leader torque changed; following stopped.')
                    targets=self.follow_targets()
                elif self.mode=='pose':targets=self.fixed_targets
                else:
                    frames=self.play_frames;elapsed=self.clock()-self.started
                    while self.play_index+1<len(frames) and frames[self.play_index]['t']<elapsed:self.play_index+=1
                    current=frames[self.play_index]
                    previous=frames[self.play_index-1] if self.play_index else dict(t=0.,roles={'follower':self.play_start})
                    fraction=max(0.,min(1.,(elapsed-previous['t'])/(current['t']-previous['t'])))
                    targets={n:previous['roles']['follower'][n]+fraction*(current['roles']['follower'][n]-previous['roles']['follower'][n]) for n in JOINT_NAMES}
                    if elapsed>=frames[-1]['t']:
                        calibration=follower.controller.calibration
                        settled=all(abs(calibration.encode(n,targets[n])-s['sample']['motors'][i]['position'])<=16 for i,n in enumerate(JOINT_NAMES,1))
                        if settled:self.stop_motion('Playback complete; follower motors released.');return
                        if elapsed>frames[-1]['t']+3:raise ValueError('Playback stopped: follower did not reach its final target.')
                follower.request('target',targets);follower.heartbeat(True)
        except (ValueError,ConnectionError,OSError) as exc:
            self.recording=False;self.stop_motion(str(exc))

    def close(self):
        self.stop_recording();self.stop_motion()
        for access in self.accesses.values():access.stop(shutdown=True,force=False)
        self.accesses={};self.loading.clear()
