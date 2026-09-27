"""LeRobot half-turn homing and guided range/mapping math; no Qt or device I/O.

Procedure follows pinned LeRobot e595b790 (Apache-2.0). Preview is explicitly
provisional until the operator confirms the reference pose and each direction.
"""
import json,math,os,tempfile
from pathlib import Path
from .robot import JOINT_NAMES,joint_limits
from .hardware_calibration import Calibration
from .joint_binding import JointBinding,RobotBinding


def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.setup-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def reference_pose(role):
    return {n:(sum(joint_limits(role)[n])/2 if n=='gripper' else 0.) for n in JOINT_NAMES}


class RangeCapture:
    def __init__(self,role,homings):
        self.role=role;self.homings=homings
        self.ranges={n:[2047,2047] for n in JOINT_NAMES}
        self.directions={n:1 for n in JOINT_NAMES};self.confirmed=set();self.last_sequence=-1
        self.reference=reference_pose(role)
    def observe(self,sample,name):
        if sample['sequence']==self.last_sequence:return
        self.last_sequence=sample['sequence']
        if any(m['torque'] for m in sample['motors'].values()):raise ValueError('Motors must remain torque-off during calibration')
        value=sample['motors'][JOINT_NAMES.index(name)+1]['position']
        low,high=self.ranges[name]
        self.ranges[name]=[min(low,value),max(high,value)]
    def confirm(self,name):
        low,high=self.ranges[name]
        if high-low<100:raise ValueError('Move this joint through its travel before confirming (at least 100 encoder ticks).')
        self.confirmed.add(name)
    def preview(self,sample):
        result={};clipped=[]
        for i,n in enumerate(JOINT_NAMES,1):
            raw=sample['motors'][i]['position']
            value=self.reference[n]+self.directions[n]*(raw-2047)*2*math.pi/4095
            low,high=joint_limits(self.role)[n]
            result[n]=max(low,min(high,value))
            if abs(result[n]-value)>.03:clipped.append(n)
        return result,clipped
    def calibration(self):
        if self.confirmed!=set(JOINT_NAMES):raise ValueError('Confirm the travel and direction of all six joints first')
        values={}
        for i,n in enumerate(JOINT_NAMES,1):
            low,high=self.ranges[n] if n!='wrist_roll' else (0,4095)
            values[n]=dict(id=i,drive_mode=0,homing_offset=self.homings[i],range_min=low,range_max=high)
        return Calibration(values)
    def binding(self,device_id):
        c=self.calibration();joints=[]
        for i,n in enumerate(JOINT_NAMES,1):
            low,high=self.ranges[n]  # Only the observed wrist interval is qualified for mapping.
            vlow,vhigh=joint_limits(self.role)[n];direction=self.directions[n]
            # Intersect the measured encoder interval with representable CAD travel.
            candidates=[2047+(v-self.reference[n])*4095/(2*math.pi*direction) for v in (vlow,vhigh)]
            low=max(low,math.ceil(min(candidates)));high=min(high,math.floor(max(candidates)))
            if high-low<32:raise ValueError(n+': reference pose does not match the virtual joint; repeat calibration')
            radians=tuple(self.reference[n]+direction*(raw-2047)*2*math.pi/4095 for raw in (low,high))
            observed=tuple(c.decode(n,raw) for raw in (low,high))
            joints.append(JointBinding(n,i,'percent' if n=='gripper' else 'degrees',observed,radians))
        return RobotBinding(self.role,device_id,c.identity,tuple(joints))
