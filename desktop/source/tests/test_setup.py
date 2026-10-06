import json, tempfile,time,unittest
from pathlib import Path
from tests import test_hardware
from lertx.usb_bus import signed
from lertx.setup_calibration import RangeCapture
from lertx.robot import JOINT_NAMES


class CalibrationSerial(test_hardware.SerialRobot):
    def write(self,packet):
        p=bytes(packet);i=p[2];r=self.registers[i]
        old_homing=signed(int.from_bytes(r[31:33],'little'),11)
        old_position=int.from_bytes(r[56:58],'little')
        result=super().write(packet)
        if p[4]==3 and p[5]==31:
            homing=signed(int.from_bytes(r[31:33],'little'),11)
            r[56:58]=((old_position+old_homing-homing)%4096).to_bytes(2,'little')
        return result


class UnwrappedCalibrationSerial(test_hardware.SerialRobot):
    """Physical firmware keeps an extended position when homing is cleared."""
    def write(self,packet):
        p=bytes(packet);r=self.registers[p[2]]
        before=signed(int.from_bytes(r[56:58],'little'),15)+signed(int.from_bytes(r[31:33],'little'),11)
        result=super().write(packet)
        if p[4]==3 and p[5]==31:
            position=before-signed(int.from_bytes(r[31:33],'little'),11)
            r[56:58]=(abs(position)|((1<<15) if position<0 else 0)).to_bytes(2,'little')
        return result


class SetupSessionTests(test_hardware.SessionTests):
    def test_extended_unoffset_reference_restores_and_maps_both_roles(self):
        self.serial=UnwrappedCalibrationSerial()
        # Positive overflow seen on the real follower, plus negative underflow.
        for i,position,homing in ((5,3968,562),(4,100,-594)):
            r=self.serial.registers[i]
            r[56:58]=position.to_bytes(2,'little')
            r[31:33]=(abs(homing)|((1<<11) if homing<0 else 0)).to_bytes(2,'little')
        self.session.calibration=None
        self.session.request('connect');self.wait(lambda s:s['state']=='read-only')
        original=self.session.bus.metadata.copy()
        self.session.request('setup_begin',self.backup)
        s=self.wait(lambda s:(s['setup'] or {}).get('state')=='recording')
        self.assertEqual(s['setup']['reference_positions'][5],2483)
        self.assertEqual(s['setup']['reference_positions'][4],1553)
        for role in ('leader','follower'):
            capture=RangeCapture(role,s['setup']['homings'],s['setup']['reference_positions'])
            pose,_=capture.preview(s['sample'])
            self.assertEqual(pose,capture.reference)
            for name,center in capture.reference_positions.items():capture.ranges[name]=[center-100,center+100]
            capture.confirmed=set(JOINT_NAMES)
            binding=capture.binding(self.session.device_id)
            calibration=capture.calibration()
            obs={n+'.pos':calibration.decode(n,s['sample']['motors'][i]['position']) for i,n in enumerate(JOINT_NAMES,1)}
            mapped=binding.map_observation(obs,device_id=self.session.device_id,calibration_id=calibration.identity,captured_at=time.monotonic(),now=time.monotonic())
            for path,value in mapped.items():self.assertAlmostEqual(value,capture.reference[path.rsplit('/',1)[-1]])
        self.session.request('setup_cancel')
        self.wait(lambda s:(s['setup'] or {}).get('state')=='cancelled')
        self.assertEqual(self.session.bus.metadata,original)
        self.assertFalse(any(address==40 and value for _,address,value,_ in self.serial.writes))

    def setUp(self):
        super().setUp()
        self.serial=CalibrationSerial()
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.backup=Path(self.directory.name)/'backup.json'
    def begin(self):
        self.connect();self.session.request('setup_begin',self.backup)
        return self.wait(lambda s:s['state']=='calibrating' and s['setup']['state']=='recording')
    def test_homing_then_cancel_restores_original_registers(self):
        s=self.begin()
        self.assertTrue(self.backup.exists())
        self.assertEqual(s['setup']['homings'],dict.fromkeys(range(1,7),1))
        self.assertTrue(all(m['position']==2047 for m in s['sample']['motors'].values()))
        self.session.request('setup_cancel')
        self.wait(lambda s:s['setup']['state']=='cancelled')
        for r in self.serial.registers.values():
            self.assertEqual(int.from_bytes(r[31:33],'little'),0)
            self.assertEqual(int.from_bytes(r[9:11],'little'),512)
            self.assertEqual(int.from_bytes(r[11:13],'little'),3584)
        self.assertFalse(any(a==40 and v for _,a,v,_ in self.serial.writes))
    def test_calibration_commit_keeps_torque_off_and_matches_import(self):
        s=self.begin();capture=RangeCapture('follower',s['setup']['homings'])
        for name in JOINT_NAMES:
            capture.ranges[name]=[1800,2300];capture.confirm(name)
        c=capture.calibration();self.session.request('setup_save',c)
        result=self.wait(lambda s:s['setup']['state']=='saved')
        self.assertEqual(result['state'],'read-only');self.assertEqual(result['calibration'],c.values)
        self.assertTrue(all(not m['torque'] for m in result['sample']['motors'].values()))
        binding=capture.binding(self.session.device_id);self.assertEqual(len(binding.joints),6)
        self.assertEqual(c.values['wrist_roll']['range_min'],0)
        self.assertEqual(c.values['wrist_roll']['range_max'],4095)
    def test_partial_write_error_restores_backup_and_faults(self):
        self.connect();original=self.session.bus.write_calibration;failed=False
        def fail_once(i,*args):
            nonlocal failed
            if i==3 and not failed:failed=True;raise ConnectionError('injected calibration failure')
            return original(i,*args)
        self.session.bus.write_calibration=fail_once
        self.session.request('setup_begin',self.backup)
        s=self.wait(lambda s:s['state']=='fault')
        self.assertIn('injected',s['error']);self.assertEqual(s['setup']['state'],'cancelled')
        self.assertEqual(int.from_bytes(self.serial.registers[1][9:11],'little'),512)
    def test_shutdown_restores_active_calibration(self):
        self.begin();self.session.stop(shutdown=True,force=False);self.session._thread.join(3)
        self.assertFalse(self.session._thread.is_alive())
        self.assertEqual(int.from_bytes(self.serial.registers[1][9:11],'little'),512)
    def test_failed_restore_stays_visible_after_shutdown(self):
        self.begin();self.serial.drop=True
        self.session.stop(shutdown=True,force=False);self.session._thread.join(3)
        s=self.session.snapshot()
        self.assertFalse(s['alive']);self.assertEqual(s['state'],'fault')
        self.assertEqual(s['setup']['state'],'restore-unconfirmed')
        self.assertIn('RESTORE UNCONFIRMED',s['error'])
        self.assertTrue(self.backup.exists())

    def test_successful_restore_does_not_hide_failed_torque_stop(self):
        self.begin();original=self.session.bus.write
        def fail_stop(i,address,value):
            if i==1 and address==40:raise ConnectionError('injected stop failure')
            return original(i,address,value)
        self.session.bus.write=fail_stop
        self.session.stop(force=True)
        self.wait(lambda s:s['setup']['state']=='cancelled')
        self.session.stop(shutdown=True,force=False);self.session._thread.join(3)
        s=self.session.snapshot()
        self.assertEqual(s['state'],'fault');self.assertIs(s['stop_confirmed'],False)
        self.assertIn('STOP UNCONFIRMED',s['error'])

    def test_torque_on_prevents_all_calibration_writes(self):
        self.connect();self.serial.registers[1][40]=1
        self.session.request('setup_begin',self.backup)
        self.wait(lambda s:s['state']=='fault')
        self.assertEqual(self.serial.writes,[]);self.assertFalse(self.backup.exists())

    def test_changed_usb_identity_never_receives_restore_writes(self):
        self.begin();count=len(self.serial.writes)
        def changed(candidate):raise ConnectionError('USB identity changed')
        self.session.verify=changed;self.session.stop(shutdown=True,force=False);self.session._thread.join(3)
        self.assertEqual(len(self.serial.writes),count)
        self.assertEqual(self.session.snapshot()['setup']['state'],'restore-unconfirmed')

    def test_calibration_restores_servo_lock(self):
        self.connect();self.serial.registers[1][55]=1
        self.session.bus.write_calibration(1,-123,400,3600)
        self.assertEqual(self.serial.registers[1][55],1)
        self.assertEqual(signed(int.from_bytes(self.serial.registers[1][31:33],'little'),11),-123)

    def test_missing_backup_directory_is_created_before_writes(self):
        self.backup=Path(self.directory.name)/'nested'/'original.json';self.begin()
        self.assertEqual(json.loads(self.backup.read_text())['role'],'follower')


class RangeTests(unittest.TestCase):
    def test_requires_every_joint_and_real_travel(self):
        c=RangeCapture('leader',dict.fromkeys(range(1,7),0))
        with self.assertRaises(ValueError):c.confirm('shoulder_pan')
        with self.assertRaises(ValueError):c.calibration()
        c.ranges['shoulder_pan']=[1900,2200];c.confirm('shoulder_pan')
        with self.assertRaises(ValueError):c.binding('test')
    def test_preview_direction_and_limits_are_explicit(self):
        c=RangeCapture('follower',dict.fromkeys(range(1,7),0))
        sample={'motors':{i:{'position':2247,'torque':False} for i in range(1,7)},'sequence':1}
        first,_=c.preview(sample);c.directions['shoulder_pan']=-1
        second,_=c.preview(sample)
        self.assertAlmostEqual(first['shoulder_pan'],-second['shoulder_pan'])
        sample['motors'][1]['position']=4095
        _,clipped=c.preview(sample);self.assertIn('shoulder_pan',clipped)
