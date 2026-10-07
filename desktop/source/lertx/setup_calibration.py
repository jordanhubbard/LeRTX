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


class JointSweep:
    """Collect a prompted end-to-end-and-back sweep of one motor only.

    A held encoder value is evidence of an operator pause, not a detected physical
    hard stop. The UI asks the operator to choose the comfortable travel limits.
    """
    HOLD_SECONDS = .7
    MIN_SAMPLES = 6
    JITTER = 12
    MAX_GAP = .25

    def __init__(self, role, name):
        self.name = name
        self.motor = JOINT_NAMES.index(name)+1
        low, high = joint_limits(role)[name]
        self.minimum_span = max(160, min(600, round((high-low)*4095/(2*math.pi)*.25)))
        self.phase = 0
        self.first = self.second = self.start = None
        self.first_interval = self.second_interval = None
        self.ready_sequence = None
        self.last_sequence = -1
        self.last_timestamp = None
        self.reset_hold()

    def reset_hold(self):
        self.anchor = None
        self.held_since = None
        self.held_values = []
        self.hold_fraction = 0.

    @property
    def complete(self):
        return self.phase == 3

    @property
    def progress(self):
        return 100 if self.complete else round((self.phase+self.hold_fraction)/3*100)

    @property
    def prompt(self):
        return ('Move to one comfortable end of travel, then pause briefly.',
                'First end recorded. Move to the opposite end, then pause briefly.',
                'Both ends recorded. Return to the first end and pause to check repeatability.',
                'Sweep captured. Waiting for the live 3D frame before continuing.')[self.phase]

    def feedback(self, sample):
        value=sample['motors'][self.motor]['position']
        if self.phase == 2:
            direction=1 if self.first>self.second else -1
            distance=max(0, direction*(self.first-value))
            return (f'Return toward the FIRST end, then hold still. Now {value} ticks; '
                    f'reach {round(self.first)} ticks or farther in that direction; {round(distance)} ticks remaining. '
                    f'Hold: {round(self.hold_fraction*100)}%.')
        return self.prompt+f' Encoder: {value} ticks. Hold: {round(self.hold_fraction*100)}%.'

    @property
    def bounds(self):
        if not self.complete:
            raise ValueError('Complete the end-to-end-and-back sweep first.')
        return [min(*self.first_interval, *self.second_interval),
                max(*self.first_interval, *self.second_interval)]

    def observe(self, sample):
        sequence, timestamp = sample['sequence'], sample['timestamp']
        if self.complete or sequence <= self.last_sequence:
            return
        if any(m['torque'] for m in sample['motors'].values()):
            self.reset_hold()
            raise ValueError('Release motor torque before capturing travel.')
        if self.last_timestamp is not None:
            if timestamp <= self.last_timestamp:
                self.reset_hold()
                return
            if timestamp-self.last_timestamp > self.MAX_GAP:
                self.reset_hold()
        self.last_sequence, self.last_timestamp = sequence, timestamp
        value = sample['motors'][self.motor]['position']
        if self.start is None:
            self.start = value
        if self.phase == 0:
            eligible = abs(value-self.start) >= 80
        elif self.phase == 1:
            eligible = abs(value-self.first) >= self.minimum_span
        else:
            # A first pause may be inside the real travel limit. Returning farther
            # toward that end is valid evidence too, not a missed narrow target.
            direction = 1 if self.first > self.second else -1
            tolerance = max(24, min(48, abs(self.second-self.first)*.03))
            eligible = direction*(value-self.first) >= -tolerance
        if not eligible:
            self.reset_hold()
            return
        if self.anchor is None or abs(value-self.anchor) > self.JITTER:
            self.anchor, self.held_since, self.held_values = value, timestamp, []
        self.held_values.append(value)
        self.hold_fraction = min(1., (timestamp-self.held_since)/self.HOLD_SECONDS)
        if self.hold_fraction < 1 or len(self.held_values) < self.MIN_SAMPLES:
            return
        interval = (min(self.held_values), max(self.held_values))
        middle = sum(interval)/2
        if self.phase == 0:
            self.first, self.first_interval = middle, interval
        elif self.phase == 1:
            self.second, self.second_interval = middle, interval
        else:
            self.first_interval = (min(self.first_interval[0], interval[0]),
                                   max(self.first_interval[1], interval[1]))
            self.ready_sequence = sequence
        self.phase += 1
        self.reset_hold()


class RangeCapture:
    def __init__(self,role,homings,reference_positions=None):
        self.role=role;self.homings=homings
        self.reference_positions={n:(reference_positions or {}).get(i,2047) for i,n in enumerate(JOINT_NAMES,1)}
        self.ranges={n:[self.reference_positions[n]]*2 for n in JOINT_NAMES}
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
            value=self.reference[n]+self.directions[n]*(raw-self.reference_positions[n])*2*math.pi/4095
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
            center=self.reference_positions[n]
            candidates=[center+(v-self.reference[n])*4095/(2*math.pi*direction) for v in (vlow,vhigh)]
            low=max(0,low,math.ceil(min(candidates)));high=min(4095,high,math.floor(max(candidates)))
            if high-low<32:raise ValueError(n+': reference pose does not match the virtual joint; repeat calibration')
            radians=tuple(self.reference[n]+direction*(raw-center)*2*math.pi/4095 for raw in (low,high))
            observed=tuple(c.decode(n,raw) for raw in (low,high))
            joints.append(JointBinding(n,i,'percent' if n=='gripper' else 'degrees',observed,radians))
        return RobotBinding(self.role,device_id,c.identity,tuple(joints))
