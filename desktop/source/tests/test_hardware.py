"""Real pinned SDK over an emulated serial byte stream; no robot required."""
import copy
import threading
import time
import unittest
from lertx.devices import Candidate
from lertx.hardware import HardwareSession
from lertx.hardware_calibration import Calibration
from lertx.robot import JOINT_NAMES
from lertx.usb_bus import FeetechBus


def calibration():
    return Calibration({n:dict(id=i,drive_mode=0,homing_offset=0,range_min=512,range_max=3584)
                        for i,n in enumerate(JOINT_NAMES,1)})


class SerialRobot:
    def __init__(self,**kwargs):
        self.settings=kwargs;self.closed=False;self.reply=bytearray();self.packets=[];self.writes=[]
        self.drop=False;self.corrupt=False;self.fault_motor=None
        self.registers={i:bytearray(256) for i in range(1,7)}
        for i,r in self.registers.items():
            r[0:2]=bytes([3,9]);r[3:5]=(777).to_bytes(2,'little');r[5]=i;r[8]=1
            r[9:11]=(512).to_bytes(2,'little');r[11:13]=(3584).to_bytes(2,'little')
            r[42:44]=(1024).to_bytes(2,'little')  # Old goal must never be reused on arm.
            r[56:58]=(2048).to_bytes(2,'little');r[62]=74;r[63]=25
    def reset_input_buffer(self):self.reply.clear()
    def close(self):self.closed=True
    def read(self,length):
        data=self.reply[:min(3,length)];del self.reply[:len(data)]
        if not data:threading.Event().wait(.001)
        return bytes(data)
    def write(self,packet):
        p=bytes(packet);self.packets.append(p)
        assert p[:2]==b'\xff\xff' and len(p)==p[3]+4 and sum(p[2:])&255==255
        motor,length,instruction=p[2:5];r=self.registers[motor]
        if instruction==2:
            address,size=p[5:7];data=bytes(r[address:address+size])
        elif instruction==3:
            address=p[5];data=p[6:-1];r[address:address+len(data)]=data
            self.writes.append((motor,address,int.from_bytes(data,'little'),time.monotonic()))
            if r[40]:r[56:58]=r[42:44]
            data=b''
        else:raise AssertionError('Unexpected SDK instruction')
        status=4 if self.fault_motor==motor else 0
        body=bytes([motor,len(data)+2,status])+data
        checksum=(~sum(body))&255
        if self.corrupt:checksum^=1
        self.reply=bytearray(b'\xff\xff'+body+bytes([checksum])) if not self.drop else bytearray()
        return len(packet)


class CalibrationTests(unittest.TestCase):
    def test_roundtrip_and_direction_match_lerobot(self):
        values=calibration().values;values['gripper']['drive_mode']=1;values['shoulder_pan']['drive_mode']=1
        c=Calibration(values)
        self.assertEqual(c.decode('gripper',512),100)
        self.assertEqual(c.decode('gripper',3584),0)
        self.assertGreater(c.decode('shoulder_pan',2500),0) # Degree mode ignores drive_mode.
        for name in JOINT_NAMES:
            for raw in (512,1024,2048,3584):self.assertEqual(c.encode(name,c.decode(name,raw)),raw)
        for value in (float('nan'),float('inf'),1000,True):
            with self.assertRaises(ValueError):c.encode('shoulder_pan',value)
    def test_invalid_id_range_and_homing_rejected(self):
        for field,value in [('id',7),('range_min',4000),('homing_offset',4000),('drive_mode',True)]:
            values=calibration().values;values['gripper'][field]=value
            with self.assertRaises(ValueError):Calibration(values)


class SDKTests(unittest.TestCase):
    def make_bus(self):
        self.serial=SerialRobot()
        self.bus=FeetechBus('test',serial_factory=lambda **kw:self.serial)
        self.addCleanup(self.bus.close)
        return self.bus
    def test_real_sdk_partial_packets_and_write_readback(self):
        bus=self.make_bus();metadata=bus.open();calibration().verify(metadata)
        self.assertEqual(bus.sample()[1]['position'],2048)
        self.assertEqual(self.serial.writes,[])
        bus.write(1,42,2100)
        self.assertEqual(self.serial.writes[0][:3],(1,42,2100))
        with self.assertRaises(ValueError):bus.write(1,31,0)
        with self.assertRaises(ValueError):bus.write(1,42,4096)
    def test_wrong_model_and_fault_packets_fail(self):
        bus=self.make_bus();self.serial.registers[1][3:5]=(12).to_bytes(2,'little')
        with self.assertRaises(ValueError):bus.open()
        self.assertTrue(self.serial.closed);self.assertEqual(self.serial.writes,[])
    def test_corrupt_and_missing_packets_have_bounded_failure(self):
        for fault in ('corrupt','drop'):
            bus=self.make_bus();bus.open();setattr(self.serial,fault,True)
            started=time.monotonic()
            with self.assertRaises(ConnectionError):bus.sample()
            self.assertLess(time.monotonic()-started,.3)
    def test_partial_read_and_temperature_fault(self):
        bus=self.make_bus();bus.open();self.serial.registers[4][63]=65
        with self.assertRaises(ValueError):bus.sample()


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.serial=SerialRobot();self.port='emulated-'+self.id()
        candidate=Candidate(self.port,123,456,'test-serial')
        self.session=HardwareSession(candidate,'follower',verify=lambda c:None,
            bus_factory=lambda port:FeetechBus(port,serial_factory=lambda **kw:self.serial))
        self.addCleanup(self.cleanup)
    def cleanup(self):
        self.session.stop(shutdown=True,force=False);self.session._thread.join(2)
        self.assertFalse(self.session._thread.is_alive())
    def wait(self,predicate,heartbeat=True,held=False,timeout=2):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if heartbeat:self.session.heartbeat(held)
            value=self.session.snapshot()
            if predicate(value):return value
            threading.Event().wait(.005)
        self.fail('Condition failed: '+repr(self.session.snapshot()))
    def connect(self):
        self.session.request('calibration',calibration());self.session.request('connect')
        return self.wait(lambda s:s['state']=='read-only')
    def arm(self):
        self.connect();self.session.request('arm')
        return self.wait(lambda s:s['state']=='armed')
    def test_readonly_connection_and_close_never_write(self):
        self.connect();self.cleanup();self.assertEqual(self.serial.writes,[])
        self.assertTrue(self.serial.closed)
    def test_arm_seeds_all_goals_before_torque_and_stops_all_motors(self):
        self.arm()
        goals=[(i,a,v) for i,a,v,t in self.serial.writes if a==42]
        self.assertEqual(goals,[(i,42,2048) for i in range(1,7)])
        first_enable=next(n for n,w in enumerate(self.serial.writes) if w[1:3]==(40,1))
        self.assertEqual(sum(w[1]==42 for w in self.serial.writes[:first_enable]),6)
        self.session.stop()
        self.wait(lambda s:s['state']=='read-only' and s['stop_confirmed'])
        self.assertTrue(all(r[40]==0 for r in self.serial.registers.values()))
    def test_held_motion_rate_limit_release_hold_and_cancelled_commands(self):
        self.arm();self.session.request('target',{'shoulder_pan':30.})
        self.wait(lambda s:1 in s['targets'] and s['targets'][1]>2200)
        self.assertEqual(self.serial.registers[1][56:58],(2048).to_bytes(2,'little'))
        self.wait(lambda s:s['sample']['motors'][1]['position']>2058,held=True)
        self.session.heartbeat(False)
        self.wait(lambda s:s['targets'][1]<2200)
        writes=[v for i,a,v,t in self.serial.writes if i==1 and a==42]
        self.assertTrue(all(abs(b-a)<=10 for a,b in zip(writes,writes[1:])))
        self.session.stop();self.session.request('target',{'shoulder_pan':20.})
        self.wait(lambda s:s['state'] in ('read-only','fault') and not self.session.owns_torque)
        self.assertTrue(all(r[40]==0 for r in self.serial.registers.values()))
    def test_heartbeat_timeout_disarms_without_renderer(self):
        self.arm()
        status=self.wait(lambda s:s['state']=='fault',heartbeat=False,timeout=2)
        self.assertIn('heartbeat',status['error']);self.assertTrue(status['stop_confirmed'])
        self.assertTrue(self.serial.closed)
    def test_bus_loss_is_unconfirmed_stop_not_success(self):
        self.arm();self.serial.drop=True
        status=self.wait(lambda s:s['state']=='fault' and not s['alive'] or s['stop_confirmed'] is False,timeout=2)
        self.assertIn('UNCONFIRMED',status['error'])
        self.assertFalse(status['stop_confirmed'])
        self.wait(lambda s:self.session.bus is None)
        self.session.stop()
        status=self.wait(lambda s:not self.session._stop.is_set())
        self.assertIn('UNCONFIRMED',status['error'])
        self.assertFalse(status['stop_confirmed'])

    def test_changed_motor_calibration_is_checked_again_before_arm(self):
        self.connect();self.serial.registers[1][9:11]=(600).to_bytes(2,'little')
        self.session.request('arm');status=self.wait(lambda s:s['state']=='fault')
        self.assertIn('calibration',status['error']);self.assertEqual(self.serial.writes,[])
    def test_bad_calibration_and_preexisting_torque_block_arming(self):
        self.connect();self.serial.registers[1][40]=1;self.session.request('arm')
        self.wait(lambda s:s['state']=='fault')
        self.assertEqual(self.serial.writes,[])
    def test_motor_error_during_arm_cleans_up_partial_enables(self):
        self.connect()
        original=self.serial.write
        def failing(packet):
            p=bytes(packet)
            result=original(packet)
            if p[4]==3 and p[5]==40 and p[6]==1 and p[2]==3:
                self.serial.reply[-1]^=1
            return result
        self.serial.write=failing
        self.session.request('arm');status=self.wait(lambda s:s['state']=='fault')
        self.assertTrue(all(r[40]==0 for r in self.serial.registers.values()))


@unittest.skipUnless(__import__('os').name=='posix','POSIX serial endpoint test')
class SerialEndpointTests(unittest.TestCase):
    def test_real_pyserial_port_with_sdk_packets(self):
        import os
        import select
        import tty
        master,slave=os.openpty();tty.setraw(slave)
        endpoint=os.ttyname(slave);robot=SerialRobot();stopped=threading.Event();failures=[]
        def server():
            buffer=bytearray()
            try:
                while not stopped.is_set():
                    readable,_,_=select.select([master],[],[],.05)
                    if not readable:continue
                    buffer.extend(os.read(master,4096))
                    while len(buffer)>=4 and len(buffer)>=buffer[3]+4:
                        count=buffer[3]+4;packet=bytes(buffer[:count]);del buffer[:count]
                        robot.write(packet)
                        response=bytes(robot.reply);robot.reply.clear()
                        os.write(master,response)
            except Exception as exc:failures.append(exc)
        thread=threading.Thread(target=server,daemon=True);thread.start()
        # macOS PTYs do not implement the IOSSIOSPEED ioctl for 1 Mbps.
        # A PTY has no physical baud clock: use a standard speed there while
        # retaining the real pyserial endpoint and SDK packet exchange.
        import sys
        import serial
        def serial_factory(**kwargs):
            if sys.platform == 'darwin':kwargs['baudrate']=115200
            return serial.Serial(**kwargs)
        bus=FeetechBus(endpoint,serial_factory=serial_factory)
        try:
            bus.open();self.assertEqual(bus.sample()[6]['position'],2048)
            bus.write(2,42,2090)
            self.assertEqual(int.from_bytes(bus.read(2,42,2),'little'),2090)
            self.assertEqual(robot.writes[0][:3],(2,42,2090))
        finally:
            bus.close();stopped.set();thread.join(1);os.close(slave);os.close(master)
        self.assertEqual(failures,[])


class BindingFileTests(unittest.TestCase):
    def test_saved_binding_roundtrip_and_identity_guards(self):
        from lertx.joint_binding import JointBinding,RobotBinding
        from lertx.hardware_calibration import save_binding,load_binding,binding_targets
        from lertx.robot import joint_limits
        import tempfile
        from pathlib import Path
        c=calibration();joints=[]
        for i,name in enumerate(JOINT_NAMES,1):
            low,high=joint_limits('follower')[name]
            angles=(low+(high-low)*.4,low+(high-low)*.6)
            joints.append(JointBinding(name,i,'percent' if name=='gripper' else 'degrees',
                (20.,80.) if name=='gripper' else (-10.,10.),angles))
        binding=RobotBinding('follower','device',c.identity,tuple(joints))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'binding.json';save_binding(path,binding)
            loaded=load_binding(path,'follower','device',c)
            targets=binding_targets(loaded,{j.name:sum(j.radians)/2 for j in loaded.joints})
            self.assertAlmostEqual(targets['gripper'],50.)
            self.assertAlmostEqual(targets['shoulder_pan'],0.)
            with self.assertRaises(ValueError):load_binding(path,'leader','device',c)
            with self.assertRaises(ValueError):load_binding(path,'follower','different-device',c)
            bad={j.name:sum(j.radians)/2 for j in loaded.joints};bad['gripper']=100
            with self.assertRaises(ValueError):binding_targets(loaded,bad)
