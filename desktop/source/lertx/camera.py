"""One application-owned camera capture, shared by all preview surfaces."""
import json
import time
import sys
from pathlib import Path
from PySide6.QtCore import QObject,Signal,QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton
from .setup_calibration import save_json


def camera_identity(raw_id,platform=sys.platform,by_id=Path('/dev/v4l/by-id')):
    """Never persist Linux enumeration numbers as physical camera identities."""
    if platform.startswith('linux'):
        node=Path(raw_id.decode('utf-8',errors='replace'))
        if by_id.is_dir():
            for link in sorted(by_id.iterdir()):
                try:
                    if link.resolve()==node.resolve():return 'linux-by-id:'+link.name,True
                except OSError:continue
        return 'session:'+raw_id.hex(),False
    return raw_id.hex(),platform=='win32'


class QtCameraBackend(QObject):
    frame=Signal(object)
    failed=Signal(str)
    devices_changed=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        from PySide6.QtMultimedia import QMediaDevices
        self.media=QMediaDevices(self)
        self.media.videoInputsChanged.connect(self.devices_changed)
        self.camera=self.capture=self.sink=None

    def devices(self):
        result=[]
        for d in self.media.videoInputs():
            identity,persistent=camera_identity(bytes(d.id()))
            result.append(dict(id=identity,name=d.description(),persistent=persistent))
        return result

    def start(self,identity):
        from PySide6.QtMultimedia import QCamera,QMediaCaptureSession,QVideoSink
        device=next((d for d in self.media.videoInputs() if camera_identity(bytes(d.id()))[0]==identity),None)
        if device is None:raise ValueError('Selected camera is disconnected. Select an attached camera.')
        self.stop()
        camera=QCamera(device,self);self.camera=camera
        self.capture=QMediaCaptureSession(self);self.sink=QVideoSink(self)
        self.sink.videoFrameChanged.connect(lambda f:self.receive(camera,f))
        camera.errorOccurred.connect(lambda error,message:self.failed.emit(message) if self.camera is camera else None)
        self.capture.setCamera(camera);self.capture.setVideoSink(self.sink)
        camera.start()

    def receive(self,camera,frame):
        if camera is not self.camera:return
        image=frame.toImage()
        if not image.isNull():self.frame.emit(image.copy())

    def stop(self):
        camera,self.camera=self.camera,None
        if camera:camera.stop();camera.deleteLater()
        if self.capture:self.capture.setCamera(None);self.capture.setVideoSink(None);self.capture.deleteLater()
        if self.sink:self.sink.deleteLater()
        self.capture=self.sink=None


class CameraService(QObject):
    changed=Signal()
    frame_ready=Signal(object)

    def __init__(self,config_path,parent=None,backend=None,clock=time.monotonic):
        super().__init__(parent)
        self.path=Path(config_path).with_name('camera.json');self.clock=clock
        self.backend=backend or QtCameraBackend(self)
        self.selected_id='';self.active_id='';self.enabled=False
        self.image=None;self.frame_at=None;self.started_at=None;self.status='Camera disabled'
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('schema')==1 and isinstance(data.get('device_id'),str):self.selected_id=data['device_id']
        except (OSError,ValueError,AttributeError):pass
        self.backend.frame.connect(self.receive);self.backend.failed.connect(self.fail)
        self.backend.devices_changed.connect(self.refresh)
        self.timer=QTimer(self);self.timer.timeout.connect(self.check_age);self.timer.start(500)

    def devices(self):return self.backend.devices()

    def preview(self,identity):
        if not any(d['id']==identity for d in self.devices()):raise ValueError('Select an attached camera first.')
        self.disable()
        self.active_id=identity;self.enabled=True;self.started_at=self.clock()
        self.status='Starting selected camera…';self.changed.emit()
        try:self.backend.start(identity)
        except Exception as exc:self.fail(str(exc))

    def use_camera(self,identity):
        if not self.enabled or self.active_id!=identity or self.frame_at is None or self.clock()-self.frame_at>2:
            raise ValueError('Preview this camera and wait for a live image before choosing Use this camera.')
        device=next((d for d in self.devices() if d['id']==identity),None)
        if device is None:raise ValueError('Selected camera was disconnected. Preview an attached camera first.')
        persistent=device.get('persistent',False)
        save_json(self.path,dict(schema=1,device_id=identity if persistent else ''))
        self.selected_id=identity
        self.status='Camera enabled · '+('selection saved' if persistent else 'session-only identity; select again after restart')
        self.changed.emit()

    def disable(self):
        self.enabled=False;self.active_id='';self.backend.stop()
        self.image=None;self.frame_at=None;self.started_at=None;self.status='Camera disabled'
        self.frame_ready.emit(None);self.changed.emit()

    def fail(self,message):
        self.disable();self.status='Camera unavailable: '+message;self.changed.emit()

    def receive(self,image):
        if not self.enabled:return
        self.image=image;self.frame_at=self.clock()
        self.status='LIVE · '+next((d['name'] for d in self.devices() if d['id']==self.active_id),'Camera')
        self.frame_ready.emit(image);self.changed.emit()

    def refresh(self):
        devices=self.devices()
        if self.selected_id.startswith('session:') and not any(d['id']==self.selected_id for d in devices):self.selected_id=''
        if self.enabled and not any(d['id']==self.active_id for d in devices):
            self.fail('Selected camera was disconnected. Reconnect and explicitly enable it again.')
        else:self.changed.emit()

    def check_age(self):
        if not self.enabled:return
        if self.frame_at is None:
            if self.clock()-self.started_at>8:self.fail('No frames received. Check camera permissions or another application using it.')
        elif self.clock()-self.frame_at>2:
            self.image=None;self.frame_ready.emit(None)
            self.status='Camera feed stale · waiting for fresh frames';self.changed.emit()

    def close(self):self.timer.stop();self.disable()


class CameraPreview(QWidget):
    def __init__(self,service,parent=None,hide_disabled=True):
        super().__init__(parent)
        from .setup_visuals import NativeSetupView
        self.service=service;self.hide_disabled=hide_disabled
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.label=QLabel();self.label.setWordWrap(True);layout.addWidget(self.label)
        self.view=NativeSetupView(self);self.view.empty_message='Select a camera in Device Manager and choose Preview selected camera.';self.view.setAccessibleName('Live USB camera preview');layout.addWidget(self.view,1)
        self.disable=QPushButton('Disable camera');self.disable.clicked.connect(service.disable);layout.addWidget(self.disable)
        service.frame_ready.connect(self.view.set_image);service.changed.connect(self.refresh)
        self.view.set_image(service.image);self.refresh()

    def refresh(self):
        self.label.setText(self.service.status)
        self.disable.setEnabled(self.service.enabled)
        if self.hide_disabled:self.setVisible(self.service.enabled)
