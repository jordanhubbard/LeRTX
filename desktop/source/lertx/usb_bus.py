"""Bounded Feetech SDK transport for the reviewed SO-101 register subset.

Register definitions match LeRobot e595b7902714ba51f91e47523f66f89c5181b649.
The upstream SDK is vendored unchanged; only its port implementation is adapted.
"""
import os
import time

IDS = tuple(range(1, 7))
# Manual motion uses volatile SRAM only; write_calibration is a separate torque-off path.
WRITABLE = {40: (1, 0, 1), 41: (1, 1, 10), 42: (2, 0, 4095),
            46: (2, 1, 100), 48: (2, 1, 300)}


def signed(value, bit):
    return -(value & ~(1 << bit)) if value & (1 << bit) else value


def port_key(port):
    return port.upper().removeprefix('\\\\.\\') if os.name == 'nt' else os.path.realpath(port)


def verify_attachment(candidate):
    from serial.tools import list_ports
    matches = [p for p in list_ports.comports() if port_key(p.device) == port_key(candidate.port)]
    if len(matches) != 1:
        raise ConnectionError('Selected USB attachment is missing or ambiguous')
    p = matches[0]
    if (p.vid, p.pid, p.serial_number or '') != (candidate.vendor, candidate.product, candidate.serial):
        raise ConnectionError('USB identity changed; select and confirm the device again')
    if candidate.serial and sum((q.vid,q.pid,q.serial_number)==(p.vid,p.pid,p.serial_number) for q in list_ports.comports()) != 1:
        raise ConnectionError('USB serial identity is ambiguous')


class FeetechBus:
    def __init__(self, port, serial_factory=None):
        from .vendor import feetech as sdk
        import serial
        factory = serial_factory or serial.Serial
        class BoundedPort(sdk.PortHandler):
            def setupPort(self, baud):
                self.ser = factory(port=self.port_name, baudrate=baud, timeout=.002, write_timeout=.05,
                                   **({'exclusive': True} if os.name != 'nt' else {}))
                self.is_open = True
                self.ser.reset_input_buffer()
                self.tx_time_per_byte = 10000. / baud
                return True
            def getCurrentTime(self):
                return time.monotonic()*1000
            def setPacketTimeout(self, packet_length):
                # LeRobot's correction to the published SDK timeout, bounded.
                self.setPacketTimeoutMillis(50 + self.tx_time_per_byte*(packet_length+3))
            def clearPort(self):
                # SDK flush() can block indefinitely on some USB drivers.
                self.ser.reset_input_buffer()
        self.port = BoundedPort(port)
        self.packet = sdk.PacketHandler(0)
        self.metadata = {}

    def open(self):
        try:
            if not self.port.openPort():
                raise ConnectionError('Cannot open the selected serial port at 1 Mbps')
            self.inspect()
        except Exception:
            self.close()
            raise
        return self.metadata

    def inspect(self):
        for motor in IDS:
            data = self.read(motor, 0, 40)
            word = lambda offset: int.from_bytes(bytes(data[offset:offset+2]), 'little')
            if word(3) != 777 or data[5] != motor:
                raise ValueError(f'Motor {motor}: expected STS3215 model 777 and matching ID')
            if data[33] != 0:
                raise ValueError(f'Motor {motor}: configure position mode with LeRobot before connecting')
            self.metadata[motor] = dict(model=word(3), firmware=[data[0],data[1]],
                minimum=word(9), maximum=word(11), homing=signed(word(31),11))
        if len({tuple(m['firmware']) for m in self.metadata.values()}) != 1:
            raise ValueError('Motor firmware versions differ; check the arm setup')
        return self.metadata

    def read(self, motor, address, size):
        try:
            data, communication, error = self.packet.readTxRx(self.port, motor, address, size)
            if communication != 0 or error or len(data) != size:
                raise ConnectionError(f'Motor {motor}: read failed (communication {communication}, status {error})')
            return bytes(data)
        finally:
            self.port.is_using = False

    def write(self, motor, address, value):
        if motor not in IDS or address not in WRITABLE:
            raise ValueError('Register write is outside the SO-101 manual-control contract')
        size, low, high = WRITABLE[address]
        if type(value) is not int or not low <= value <= high:
            raise ValueError('Register value is outside the bounded write range')
        self._write_checked(motor,address,size,value)

    def _write_checked(self,motor,address,size,value):
        try:
            communication, error = self.packet.writeTxRx(self.port, motor, address, size, list(value.to_bytes(size,'little')))
            if communication != 0 or error:
                raise ConnectionError(f'Motor {motor}: write not acknowledged (communication {communication}, status {error})')
            if int.from_bytes(self.read(motor,address,size),'little') != value:
                raise ConnectionError(f'Motor {motor}: register readback did not match')
        finally:
            self.port.is_using = False

    def write_calibration(self,motor,homing,minimum,maximum):
        """Explicit torque-off calibration transaction, unavailable to manual writes."""
        if motor not in IDS or any(type(v) is not int for v in (homing,minimum,maximum)):
            raise ValueError('Invalid calibration motor or value')
        if not -2047<=homing<=2047 or not 0<=minimum<maximum<=4095:
            raise ValueError('Invalid calibration limits')
        identity=self.read(motor,3,3)
        if int.from_bytes(identity[:2],'little')!=777 or identity[2]!=motor:
            raise ValueError('Calibration motor identity changed')
        if self.read(motor,40,1)!=b'\0':raise ValueError('Release motor torque before calibration')
        lock=self.read(motor,55,1)[0]
        if lock not in (0,1):raise ValueError('Invalid EEPROM lock state')
        try:
            self._write_checked(motor,55,1,0)
            # Expand first so changing the coordinate offset cannot leave crossed limits.
            self._write_checked(motor,9,2,0)
            self._write_checked(motor,11,2,4095)
            encoded=abs(homing)|((1<<11) if homing<0 else 0)
            self._write_checked(motor,31,2,encoded)
            self._write_checked(motor,9,2,minimum)
            self._write_checked(motor,11,2,maximum)
        finally:
            self._write_checked(motor,55,1,lock)

    def sample(self, *, unoffset=False, calibration_capture=False):
        result = {}
        for motor in IDS:
            data = self.read(motor,40,31)
            word = lambda offset: int.from_bytes(data[offset:offset+2],'little')
            position = signed(word(16),15)
            extended=unoffset or (calibration_capture and motor==5)
            low,high=(-2047,6142) if extended else (0,4095)
            if not low <= position <= high or data[0] not in (0,1):
                raise ValueError(f'Motor {motor}: encoder {position} outside {low}..{high} or invalid torque status {data[0]}')
            if (unoffset or calibration_capture) and data[0]:
                raise ValueError(f'Motor {motor}: release torque before reading extended calibration positions')
            if data[25] or data[23] >= 60:
                raise ValueError(f'Motor {motor}: fault status {data[25]}, temperature {data[23]} C')
            result[motor] = dict(position=position, torque=bool(data[0]), velocity=signed(word(18),15),
                load=signed(word(20),10), voltage=data[22]/10, temperature=data[23],current=word(29))
        return result

    def close(self):
        if self.port.ser is not None:
            self.port.closePort()
