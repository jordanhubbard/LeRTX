# Normalization adapted from LeRobot, Copyright 2024 The HuggingFace Inc. team.
# Licensed under Apache-2.0; see resources/so101/lerobot-LICENSE.
"""Strict LeRobot calibration import, explicit units and reversible bindings.

Normalization follows LeRobot motors_bus.py at e595b7902714ba51f91e47523f66f89c5181b649
(Apache-2.0): degrees ignore drive_mode; percent applies its inversion.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from .robot import JOINT_NAMES
from .joint_binding import RobotBinding, JointBinding, finite


def save_binding(path, binding):
    from dataclasses import asdict
    path=Path(path)
    fd,temporary=tempfile.mkstemp(prefix='.binding-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump({'schema':1,**asdict(binding)},stream,indent=2)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def read_json(path):
    data=Path(path).read_bytes()
    if len(data)>65536: raise ValueError('Calibration file is too large')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate calibration field')
            result[key]=value
        return result
    return json.loads(data,object_pairs_hook=unique)


class Calibration:
    def __init__(self, values):
        if not isinstance(values,dict) or set(values)!=set(JOINT_NAMES):
            raise ValueError('Calibration must contain exactly the six SO-101 joints')
        fields={'id','drive_mode','homing_offset','range_min','range_max'}
        for index,name in enumerate(JOINT_NAMES,1):
            v=values[name]
            if not isinstance(v,dict) or set(v)!=fields or any(type(x) is not int for x in v.values()):
                raise ValueError(f'{name}: invalid LeRobot calibration record')
            if v['id']!=index or v['drive_mode'] not in (0,1) or not -2047<=v['homing_offset']<=2047 or not 0<=v['range_min']<v['range_max']<=4095:
                raise ValueError(f'{name}: invalid motor ID, direction, homing or range')
        self.values=json.loads(json.dumps(values))
        self.identity=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    @classmethod
    def load(cls,path):return cls(read_json(path))

    def verify(self,metadata):
        for name,c in self.values.items():
            m=metadata[c['id']]
            if (c['homing_offset'],c['range_min'],c['range_max'])!=(m['homing'],m['minimum'],m['maximum']):
                raise ValueError(f'{name}: calibration does not match motor registers; calibrate using LeRobot')

    def decode(self,name,ticks):
        c=self.values[name];low,high=c['range_min'],c['range_max']
        if not finite(ticks) or not low<=ticks<=high:raise ValueError(f'{name}: reading outside calibrated range')
        if name=='gripper':
            value=100*(ticks-low)/(high-low)
            return 100-value if c['drive_mode'] else value
        return (ticks-(low+high)/2)*360/4095

    def limits(self,name):
        c=self.values[name]
        return tuple(sorted((self.decode(name,c['range_min']),self.decode(name,c['range_max']))))

    def encode(self,name,value):
        low,high=self.limits(name)
        if not finite(value) or not low<=value<=high:raise ValueError(f'{name}: target outside calibrated range')
        c=self.values[name]
        if name=='gripper':
            fraction=(100-value if c['drive_mode'] else value)/100
            raw=c['range_min']+fraction*(c['range_max']-c['range_min'])
        else:raw=value*4095/360+(c['range_min']+c['range_max'])/2
        return max(c['range_min'],min(c['range_max'],round(raw)))


def load_binding(path, role, device_id, calibration):
    value=read_json(path)
    if not isinstance(value,dict) or set(value)!={'schema','role','device_id','calibration_id','joints'} or value['schema']!=1:
        raise ValueError('Invalid virtual joint binding')
    if value['role']!=role or value['device_id']!=device_id or value['calibration_id']!=calibration.identity:
        raise ValueError('Binding belongs to a different device, role or calibration')
    joints=tuple(JointBinding(**j) for j in value['joints'])
    binding=RobotBinding(role,device_id,calibration.identity,joints)
    for j in joints:
        if j.unit!=('percent' if j.name=='gripper' else 'degrees'):
            raise ValueError('Hardware bindings require degree or gripper-percent observations')
        for observation in j.observed:calibration.encode(j.name,observation)
    return binding


def binding_targets(binding, radians):
    if set(radians)!=set(JOINT_NAMES):raise ValueError('Virtual pose must contain all six joints')
    result={}
    for joint in binding.joints:
        v=radians[joint.name]
        if not finite(v) or not min(joint.radians)<=v<=max(joint.radians):
            raise ValueError(f'{joint.name}: virtual target is outside measured binding')
        fraction=(v-joint.radians[0])/(joint.radians[1]-joint.radians[0])
        result[joint.name]=joint.observed[0]+fraction*(joint.observed[1]-joint.observed[0])
    return result
