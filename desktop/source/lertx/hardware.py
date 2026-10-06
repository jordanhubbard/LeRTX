"""Independent serial owner and manual-motion state machine. No GPU or Qt imports."""
import copy
import hashlib
import json
import queue
import threading
import time
from uuid import uuid4
from .robot import JOINT_NAMES
from .usb_bus import FeetechBus, IDS, port_key, verify_attachment

_PORTS=set()
_PORT_LOCK=threading.Lock()


class HardwareSession:
    PERIOD=.05
    STALE=.25
    HEARTBEAT=.5
    SPEED=100  # encoder ticks/second, also written into each servo's speed limit

    def __init__(self,candidate,role,*,bus_factory=FeetechBus,verify=verify_attachment,clock=time.monotonic):
        if role not in ('leader','follower'):raise ValueError('Invalid robot role')
        self.candidate,self.role=candidate,role
        self.device_id=candidate.identity or 'session:'+uuid4().hex
        self.bus_factory,self.verify,self.clock=bus_factory,verify,clock
        self.bus=None;self.calibration=None;self.owns_torque=False
        self.targets={};self.sent={};self.latest=None;self.sequence=0
        self.setup=None;self._setup_backup=None;self._previous_calibration=None
        self._lock=threading.Lock();self._commands=queue.Queue(maxsize=8)
        self._stop=threading.Event();self._disconnect=threading.Event();self._shutdown=threading.Event()
        self._wake=threading.Event();self._force_stop=False;self._epoch=0;self._held=False;self._was_held=False
        self._heartbeat=clock();self._state='disconnected';self._error='';self._stop_confirmed=None
        self._last_step=clock();self._claimed=False
        self._stop_completed=0
        self._thread=threading.Thread(target=self._run,name='SO101-'+role,daemon=True)
        self._thread.start()

    def request(self,command,payload=None):
        if command not in ('connect','calibration','arm','target','setup_begin','setup_save','setup_cancel'):raise ValueError('Unknown hardware command')
        with self._lock:
            if self._shutdown.is_set():raise ValueError('Hardware session is closing')
            item=(self._epoch,self.clock(),command,payload)
        try:self._commands.put_nowait(item)
        except queue.Full:raise ValueError('Hardware operation queue is busy') from None
        self._wake.set()

    def heartbeat(self,held=False):
        with self._lock:self._heartbeat=self.clock();self._held=bool(held)
        self._wake.set()

    def stop(self,*,disconnect=False,shutdown=False,force=True):
        with self._lock:
            self._epoch+=1;self._held=False;self._force_stop|=force
            request=self._epoch
        if disconnect or shutdown:self._disconnect.set()
        if shutdown:self._shutdown.set()
        self._stop.set();self._wake.set()
        return request

    def snapshot(self):
        with self._lock:
            result=copy.deepcopy(dict(state=self._state,error=self._error,sample=self.latest,
                calibration=self.calibration.values if self.calibration else None,
                targets=self.targets,stop_confirmed=self._stop_confirmed,stop_completed=self._stop_completed,device_id=self.device_id))
            result['setup']=copy.deepcopy(self.setup)
        result['alive']=self._thread.is_alive()
        if result['sample'] and self.clock()-result['sample']['timestamp']>self.STALE:
            result['stale']=True
        else:result['stale']=False
        return result

    def _state_is(self,state,error=''):
        with self._lock:self._state=state;self._error=error

    def _check_cancel(self):
        if self._stop.is_set():raise InterruptedError('Hardware operation cancelled')
        if (self.owns_torque or self._setup_backup is not None) and self.clock()-self._heartbeat>self.HEARTBEAT:
            raise ConnectionError('Hardware panel heartbeat expired')

    def _connect(self):
        if self.bus:raise ValueError('Device is already connected')
        self.verify(self.candidate)
        key=port_key(self.candidate.port)
        with _PORT_LOCK:
            if key in _PORTS:raise ValueError('This serial port already has a hardware owner')
            _PORTS.add(key);self._claimed=True
        self._state_is('connecting')
        self._stop_confirmed=None
        if not self.candidate.identity:
            self.device_id='session:'+uuid4().hex
        try:
            self.bus=self.bus_factory(self.candidate.port)
            metadata=self.bus.open()
            if self.calibration:self.calibration.verify(metadata)
            self._read()
            self._state_is('read-only')
        except Exception:
            self._close_bus();raise

    def _close_bus(self):
        if self.bus:
            try:self.bus.close()
            finally:self.bus=None
        if self._claimed:
            with _PORT_LOCK:_PORTS.discard(port_key(self.candidate.port))
            self._claimed=False
        with self._lock:self.latest=None;self.targets={}

    def _read(self):
        started=self.clock();motors=self.bus.sample()
        if set(motors)!=set(IDS) or self.clock()-started>self.STALE:
            raise ConnectionError('Incomplete or stale motor sample')
        observations={};calibration_error=''
        if self.calibration:
            try:observations={n:self.calibration.decode(n,motors[i]['position']) for i,n in enumerate(JOINT_NAMES,1)}
            except ValueError as exc:calibration_error=str(exc)
        self.sequence+=1
        sample=dict(timestamp=started,sequence=self.sequence,motors=motors,observations=observations,
                    calibration_error=calibration_error)
        with self._lock:self.latest=sample
        if self.owns_torque and calibration_error:raise ValueError(calibration_error)
        return sample

    def _fresh(self):
        if not self.latest or self.clock()-self.latest['timestamp']>self.STALE:
            raise ConnectionError('Fresh complete telemetry is required')
        if self.latest['calibration_error']:raise ValueError(self.latest['calibration_error'])
        if self.clock()-self._heartbeat>self.HEARTBEAT:
            raise ConnectionError('Hardware panel heartbeat expired')

    def _arm(self):
        if self._setup_backup is not None:raise ValueError('Finish or cancel calibration before enabling motors')
        if not self.bus or self.owns_torque or not self.calibration:
            raise ValueError('Connect read-only and load matching calibration before arming')
        self.calibration.verify(self.bus.inspect())
        self._read();self._fresh()
        if any(m['torque'] for m in self.latest['motors'].values()):
            raise ValueError('Motors already have torque enabled. Support the arm and use Release motors before engaging here.')
        self._state_is('arming');self._stop_confirmed=None
        self.owns_torque=True  # Any partially successful arm must run torque-off cleanup.
        try:
            for i in IDS:
                self._check_cancel()
                self.bus.write(i,46,self.SPEED)
                self.bus.write(i,41,10)
                self.bus.write(i,48,300)
            self._read();self._fresh()
            self.sent={i:m['position'] for i,m in self.latest['motors'].items()}
            self.targets=dict(self.sent)
            for i in IDS:
                self._check_cancel();self.bus.write(i,42,self.sent[i])
            self._read();self._fresh()
            if any(abs(self.latest['motors'][i]['position']-self.sent[i])>16 for i in IDS):
                raise ValueError('The arm moved while enabling motors; support it and retry')
            for i in IDS:
                self._check_cancel();self.bus.write(i,40,1)
            self._last_step=self.clock();self._was_held=False
            with self._lock:self._held=False
            self._read();self._state_is('armed')
        except Exception:
            self._release_torque();raise

    def _setup_begin(self,backup_path):
        from .setup_calibration import save_json
        if not self.bus or self.owns_torque or self._setup_backup is not None:
            raise ValueError('Connect read-only before starting a new calibration')
        self.verify(self.candidate)
        metadata=copy.deepcopy(self.bus.inspect());self._read()
        if any(m['torque'] for m in self.latest['motors'].values()):
            raise ValueError('Support the arm and release torque before calibration')
        # A durable backup precedes the first persistent write.
        save_json(backup_path,dict(schema=1,device_id=self.device_id,role=self.role,motors=metadata))
        self._setup_backup=metadata;self._previous_calibration=self.calibration
        self.calibration=None;self.setup={'state':'homing','backup':str(backup_path)}
        self._state_is('calibrating')
        for i in IDS:
            self._check_cancel();self.bus.write_calibration(i,0,0,4095)
        self._read()
        homings={i:m['position']-2047 for i,m in self.latest['motors'].items()}
        if any(not -2047<=v<=2047 for v in homings.values()):
            raise ValueError('Encoder is at its wrap boundary; slightly reposition the reference and retry')
        for i in IDS:
            self._check_cancel();self.bus.write_calibration(i,homings[i],0,4095)
        self._read()
        if any(abs(m['position']-2047)>24 for m in self.latest['motors'].values()):
            raise ValueError('Arm moved during homing; hold the reference pose still and retry')
        self.bus.inspect();self.setup={'state':'recording','homings':homings,'backup':str(backup_path)}
        self._state_is('calibrating')

    def _setup_save(self,calibration):
        if self._setup_backup is None or not self.bus or self.setup['state']!='recording':
            raise ValueError('Start reference calibration before saving')
        self.verify(self.candidate);self._read()
        if any(m['torque'] for m in self.latest['motors'].values()):raise ValueError('Torque must remain off')
        for i,name in enumerate(JOINT_NAMES,1):
            self._check_cancel();c=calibration.values[name]
            if c['homing_offset']!=self.setup['homings'][i]:raise ValueError('Homing identity changed')
            self.bus.write_calibration(i,c['homing_offset'],c['range_min'],c['range_max'])
        calibration.verify(self.bus.inspect())
        self.calibration=calibration;self._setup_backup=None;self._previous_calibration=None
        self.setup={**self.setup,'state':'saved'};self._read();self._state_is('read-only')

    def _setup_restore(self):
        if self._setup_backup is None:return not (self.setup and self.setup.get('state')=='restore-unconfirmed')
        errors=[]
        try:self.verify(self.candidate)
        except Exception as exc:errors.append(str(exc))
        if not errors and self.bus:
            for i,m in self._setup_backup.items():
                try:self.bus.write_calibration(i,m['homing'],m['minimum'],m['maximum'])
                except Exception as exc:errors.append(str(exc))
        elif not self.bus:errors.append('Serial connection unavailable')
        if not errors and self.bus:
            try:self.bus.inspect();self._read()
            except Exception as exc:errors.append(str(exc))
        self._setup_backup=None
        if errors:
            self.setup={**(self.setup or {}),'state':'restore-unconfirmed'}
            self.calibration=None
            self._state_is('fault','CALIBRATION RESTORE UNCONFIRMED. Original registers are in the backup file. '+errors[0])
            return False
        self.calibration=self._previous_calibration;self._previous_calibration=None
        self.setup={**(self.setup or {}),'state':'cancelled'}
        if self._stop_confirmed is False:
            self._state_is('fault','STOP UNCONFIRMED — calibration restored, but torque release was not acknowledged. Support the arm and cut motor power if needed.')
        else:self._state_is('read-only')
        return True

    def _release_torque(self,force=False):
        errors=[]
        if self._stop_confirmed is False and (not self.bus or not (self.owns_torque or force)):
            return False
        if self.bus and (self.owns_torque or force):
            for i in IDS:
                try:self.bus.write(i,40,0)
                except Exception as exc:errors.append(str(exc))
            self._stop_confirmed=not errors
        self.owns_torque=False;self._was_held=False
        with self._lock:self._held=False;self.targets={}
        if errors:
            self._state_is('fault','STOP UNCONFIRMED — cut motor power if needed. '+errors[0])
        return not errors

    def _set_target(self,values):
        if not self.owns_torque or self._state!='armed':raise ValueError('Enable motors before setting hardware targets')
        self._fresh()
        if not isinstance(values,dict) or not values or any(n not in JOINT_NAMES for n in values):
            raise ValueError('Invalid hardware joint targets')
        raw={self.calibration.values[n]['id']:self.calibration.encode(n,v) for n,v in values.items()}
        with self._lock:self.targets.update(raw)

    def _motion(self):
        self._fresh()
        if any(not m['torque'] for m in self.latest['motors'].values()):
            raise ConnectionError('A motor released torque unexpectedly')
        now=self.clock();dt=max(0.,min(now-self._last_step,.1));self._last_step=now
        with self._lock:held=self._held;targets=dict(self.targets)
        if held:
            allowance=max(0,int(self.SPEED*dt))
            for i in IDS:
                self._check_cancel()
                measured=self.latest['motors'][i]['position']
                if abs(self.sent[i]-measured)>128:raise ValueError(f'Motor {i}: tracking error; check for obstruction')
                wanted=targets.get(i,self.sent[i])
                step=max(-allowance,min(allowance,wanted-self.sent[i]))
                value=self.sent[i]+step
                if step:self.bus.write(i,42,value);self.sent[i]=value
        elif self._was_held:
            # Release cancels the remaining trajectory and holds the measured pose.
            for i in IDS:
                self._check_cancel()
                value=self.latest['motors'][i]['position']
                self.bus.write(i,42,value);self.sent[i]=value
            with self._lock:self.targets=dict(self.sent)
        self._was_held=held

    def _run(self):
        deadline=self.clock()
        try:
            while True:
                if self._stop.is_set():
                    with self._lock:force=self._force_stop;self._force_stop=False;stop_request=self._epoch
                    confirmed=self._release_torque(force)
                    restored=self._setup_restore()
                    if self._disconnect.is_set():
                        self._close_bus();self._disconnect.clear()
                        if confirmed and restored:self._state_is('disconnected')
                    elif confirmed and restored:self._state_is('read-only' if self.bus else 'disconnected')
                    with self._lock:self._stop_completed=stop_request
                    self._stop.clear()
                    if self._shutdown.is_set():break
                try:
                    try:item=self._commands.get_nowait()
                    except queue.Empty:item=None
                    if item:
                        epoch,created,command,payload=item
                        if epoch!=self._epoch:continue
                        if command in ('arm','target') and self.clock()-created>self.STALE:
                            raise ValueError('Expired hardware command; retry explicitly')
                        if command=='connect':self._connect()
                        elif command=='calibration':
                            if self.owns_torque:raise ValueError('Stop motors before changing calibration')
                            if self.bus:payload.verify(self.bus.metadata)
                            with self._lock:self.calibration=payload
                        elif command=='arm':self._arm()
                        elif command=='target':self._set_target(payload)
                        elif command=='setup_begin':self._setup_begin(payload)
                        elif command=='setup_save':self._setup_save(payload)
                        elif command=='setup_cancel':self._setup_restore()
                    now=self.clock()
                    if self.bus and now>=deadline:
                        self._read()
                        if self._setup_backup is not None and any(m['torque'] for m in self.latest['motors'].values()):
                            raise ValueError('Unexpected torque during calibration')
                        if self.owns_torque:self._motion()
                        deadline=self.clock()+self.PERIOD
                except Exception as exc:
                    if self._setup_backup is not None:self._release_torque(force=True)
                    if not self._setup_restore():
                        self._close_bus();continue
                    if self.owns_torque:
                        confirmed=self._release_torque()
                        if confirmed:self._state_is('fault',str(exc))
                    elif self._stop_confirmed is False:
                        self._state_is('fault','STOP UNCONFIRMED — cut motor power if needed. '+str(exc))
                    else:self._state_is('fault',str(exc))
                    # Never reconnect implicitly after a failed transaction.
                    self._close_bus()
                delay=max(0.,min(.05,deadline-self.clock())) if self.bus else .05
                self._wake.wait(delay);self._wake.clear()
        finally:
            try:
                self._release_torque();self._setup_restore()
            finally:self._close_bus()
