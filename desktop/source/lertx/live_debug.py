"""Opt-in loopback co-session observability. Qt owns inspection and command dispatch."""
import collections
import copy
import concurrent.futures
import hmac
import json
import os
from pathlib import Path
import queue
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class Diagnostics:
    def __init__(self, owner):
        from PySide6.QtCore import QTimer
        self.owner = owner
        self.requests = queue.Queue(maxsize=16)
        self.events = collections.deque(maxlen=1200)
        self.sequence = 0
        self.token = secrets.token_urlsafe(32)
        self.closed = False
        self.last_sample = 0.
        self.gpu = {}
        self.metrics_stop = threading.Event()
        service = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(6)

            def log_message(self, *args):
                pass

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def handle_request(self):
                if self.headers.get('Origin') or not hmac.compare_digest(
                        self.headers.get('Authorization', ''), 'Bearer '+service.token):
                    self.send_error(403)
                    return
                future = concurrent.futures.Future()
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    if not 0 <= length <= 4096:
                        raise ValueError('Request too large')
                    payload = json.loads(self.rfile.read(length)) if length else {}
                    service.requests.put_nowait((self.command, self.path, payload, future))
                    kind, body = future.result(timeout=5)
                    self.send_response(200)
                except Exception as exc:
                    future.cancel()
                    kind, body = 'application/json', json.dumps({'error': str(exc) or type(exc).__name__}).encode()
                    self.send_response(400)
                self.send_header('Content-Type', kind)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.server.timeout = .2
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
        self.thread.start()
        self.metrics_thread = threading.Thread(target=self.poll_gpu, daemon=True)
        self.metrics_thread.start()
        self.path = Path(owner.config_path).parent/'debug'/f'{os.getpid()}.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({'schema': 1, 'pid': os.getpid(),
            'url': f'http://127.0.0.1:{self.server.server_port}', 'token': self.token}), encoding='utf-8')
        self.path.chmod(0o600)
        self.timer = QTimer(owner)
        self.timer.timeout.connect(self.poll)
        self.timer.start(25)
        self.record('diagnostics.started')

    def poll_gpu(self):
        import subprocess
        while not self.metrics_stop.is_set():
            try:
                result = subprocess.run(['nvidia-smi',
                    '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
                    '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.gpu = {'at':time.monotonic(), 'scope':'whole GPU, all processes',
                            'csv':result.stdout.strip(), 'error':result.stderr.strip()}
            except (OSError, subprocess.SubprocessError) as exc:
                self.gpu = {'error':str(exc)}
            self.metrics_stop.wait(2)

    def record(self, kind, **fields):
        self.sequence += 1
        self.events.append(dict(id=self.sequence, at=time.monotonic(), kind=kind, **copy.deepcopy(fields)))

    def snapshot(self):
        owner = self.owner
        now = time.monotonic()
        devices = []
        for controller in owner.devices.active_controllers():
            sample = controller.session.snapshot()
            sample.update(role=controller.role, port=controller.candidate.port,
                          control_owner=controller._writer.purpose if controller._writer else None)
            sample['age_ms'] = (now-sample['sample']['timestamp'])*1000 if sample['sample'] else None
            devices.append(sample)
        wizard = owner._hardware_windows.get('setup') or next((w for w in self.windows()
            if hasattr(w, 'sweep') and hasattr(w, 'preview_generation')), None)
        setup = None
        if wizard:
            sweep = wizard.sweep
            setup = dict(role=wizard.role, step=wizard.step, pending=wizard.pending,
                status=wizard.status.text(), preview_error=wizard.preview_error,
                preview_pending=wizard.preview_pending, rendered_sequence=wizard.rendered_sequence,
                preview_age_ms=(now-wizard.preview_at)*1000,
                sweep=vars(sweep).copy() if sweep else None,
                next_action=sweep.prompt if sweep else None,
                ranges=wizard.capture.ranges if wizard.capture else None)
        camera=getattr(owner,'camera_service',None)
        panel=getattr(owner,'_robot_session_window',None)
        session=panel.session if panel and not panel.closed else None
        return dict(schema=1, at=now, pid=os.getpid(), ready=owner._ready,
            camera=dict(enabled=camera.enabled,selected=camera.selected_id,active=camera.active_id,
                status=camera.status,frame_age_ms=(now-camera.frame_at)*1000 if camera.frame_at is not None else None) if camera else None,
            robot_session=dict(mode=session.mode,recording=session.recording,unsaved=session.unsaved,
                frames=len(session.record['frames']) if session.record else 0,error=session.error) if session else None,
            pending_commands=len(owner._pending), target_fps=getattr(owner, '_debug_target_fps', owner.profile['rendering']['target_fps']),
            native_status=owner.native_status_label.text(), devices=devices, setup=setup,
            render=getattr(owner, '_render_diagnostics', None), gpu=self.gpu,
            cpu_seconds=sum(os.times()[:2]),
            windows=[dict(id=str(int(w.winId())), title=w.windowTitle()) for w in self.windows()])

    def windows(self):
        from PySide6.QtWidgets import QApplication
        def belongs(widget):
            while widget is not None:
                if widget is self.owner:return True
                widget = widget.parentWidget()
            return False
        return [w for w in QApplication.topLevelWidgets() if w.isVisible() and belongs(w)]

    @staticmethod
    def png(image):
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, 'PNG'):
            raise ValueError('Image capture failed')
        return bytes(buffer.data())

    def dispatch(self, method, path, payload):
        owner = self.owner
        if method == 'GET':
            if path == '/state':
                return self.snapshot()
            if path == '/events':
                return list(self.events)
            if path == '/ui':
                from PySide6.QtWidgets import QWidget, QLabel, QAbstractButton, QProgressBar, QComboBox
                result=[]
                for window in self.windows():
                    widgets=[]
                    for widget in [window, *window.findChildren(QWidget)]:
                        if not widget.isVisible():continue
                        item=dict(type=type(widget).__name__, name=widget.objectName(),
                                  enabled=widget.isEnabled(), accessible=widget.accessibleName())
                        if isinstance(widget,(QLabel,QAbstractButton)):
                            item['text']=widget.text()
                        if isinstance(widget,QAbstractButton) and widget.isCheckable():
                            item['checked']=widget.isChecked()
                        if isinstance(widget,QProgressBar):item['value']=widget.value()
                        if isinstance(widget,QComboBox):item['text']=widget.currentText()
                        widgets.append(item)
                    result.append(dict(id=str(int(window.winId())),title=window.windowTitle(),widgets=widgets))
                return result
            if path == '/frame':
                if owner._image is None:
                    raise ValueError('No frame yet')
                return self.png(owner._image)
            if path.startswith('/window/'):
                window = next((w for w in self.windows() if str(int(w.winId())) == path.split('/')[-1]), None)
                if window is None:
                    raise ValueError('No visible application window with that id')
                return self.png(window.grab())
        if method != 'POST' or path != '/command' or not isinstance(payload, dict):
            raise ValueError('Unknown diagnostic request')
        command = payload.get('command')
        if command == 'target_fps' and set(payload) == {'command', 'value'}:
            value = payload['value']
            if type(value) is not int or not 1 <= value <= 120:
                raise ValueError('target_fps must be an integer from 1 to 120')
            owner._debug_target_fps = value
            self.record('tuning.target_fps', value=value)
            return {'applied': value, 'persistent': False}
        if command == 'camera' and set(payload) <= {'command', 'orbit', 'zoom', 'role'}:
            if not owner._ready or owner._pending:
                raise ValueError('Renderer busy; retry')
            import math
            orbit, zoom = payload.get('orbit', [0, 0]), payload.get('zoom', 0)
            if not isinstance(orbit, list) or len(orbit) != 2 or any(
                    type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 2 for v in [*orbit, zoom]):
                raise ValueError('Camera deltas must be finite and within +/-2')
            role = payload.get('role')
            if role is not None and role not in ('leader', 'follower'):
                raise ValueError('Unknown arm role')
            def work():
                if role:
                    from .robot import ROOTS
                    owner.worker.frame_setup_arm(role)
                owner.worker.move_camera(orbit=orbit, zoom=zoom)
                return owner.worker.tick(0.)
            owner._command(work, owner._accept_frame)
            self.record('tuning.camera', payload=payload)
            return {'queued': True}
        raise ValueError('Unknown command or fields; physical commands are not exposed')

    def poll(self):
        now = time.monotonic()
        if now-self.last_sample >= .2:
            self.last_sample = now
            state = self.snapshot()
            self.record('state.sample', devices=state['devices'], setup=state['setup'],
                        pending_commands=state['pending_commands'])
        for _ in range(4):
            try:
                method, path, payload, future = self.requests.get_nowait()
            except queue.Empty:
                return
            if not future.set_running_or_notify_cancel():
                continue
            try:
                result = self.dispatch(method, path, payload)
                future.set_result(('image/png', result) if isinstance(result, bytes) else
                                  ('application/json', json.dumps(result, allow_nan=False).encode()))
            except Exception as exc:
                future.set_exception(exc)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.timer.stop()
        self.metrics_stop.set()
        while not self.requests.empty():
            try:
                *_, future = self.requests.get_nowait()
                if not future.done():future.set_exception(RuntimeError('Application closing'))
            except queue.Empty:
                break
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.metrics_thread.join(timeout=3.5)
        self.path.unlink(missing_ok=True)
