"""Human-facing application entry point; portable JSON remains in main.py."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time


def log_directory():
    if sys.platform=='win32':
        return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'LeRTX/logs'
    return Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'lertx/logs'


def configure_logging():
    directory=log_directory();directory.mkdir(parents=True,exist_ok=True)
    path=directory/'application.log'
    if path.exists() and path.stat().st_size>4*1024*1024:
        path.replace(directory/'application.previous.log')
    log=path.open('a',encoding='utf-8',buffering=1)
    sys.stdout=log;sys.stderr=log
    for fd in (1,2):
        try:os.dup2(log.fileno(),fd)
        except OSError:pass
    if sys.platform=='win32':
        import ctypes,msvcrt
        for which in (-11,-12):ctypes.windll.kernel32.SetStdHandle(which,msvcrt.get_osfhandle(log.fileno()))
    print('\nLeRTX desktop session',time.strftime('%Y-%m-%d %H:%M:%S'))
    return path


def main(argv=None):
    parser=argparse.ArgumentParser(prog='LeRTX',description='LeRTX robot workspace')
    parser.add_argument('scene',nargs='?',type=Path)
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--uninstall',action='store_true')
    parser.add_argument('--smoke-report',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    path=configure_logging()
    from .ui import build_application
    application=build_application([])
    if args.install or args.uninstall:
        from .installer import show_installer
        return show_installer(uninstall=args.uninstall)
    from . import app,ui
    smoke={'frame_received':False}
    if args.smoke_report:
        from PySide6.QtCore import QTimer
        original=ui.build_main_window
        def factory(*a,**kw):
            window=original(*a,**kw);timer=QTimer(window);started=time.monotonic()
            def check():
                if window._image is not None or time.monotonic()-started>90:
                    timer.stop()
                    smoke.update(frame_received=window._image is not None,seconds=round(time.monotonic()-started,3),status=window.native_status_label.text(),title=window.windowTitle(),robot_controls=window.robot_panel.isEnabled())
                    if smoke['frame_received']:
                        smoke['screenshot_saved']=window.grab().save(str(args.smoke_report.with_suffix('.png')))
                    window.close()
            timer.timeout.connect(check);timer.start(50);return window
        ui.build_main_window=factory
    try:
        result=app.main({'command':'launch',**({'scene':str(args.scene.resolve())} if args.scene else {})})
        if args.smoke_report:
            args.smoke_report.write_text(json.dumps({**smoke,**result},indent=2)+'\n')
            return 0 if smoke['frame_received'] else 1
        return 0
    except Exception as error:
        import traceback
        traceback.print_exc()
        if args.smoke_report:
            args.smoke_report.write_text(json.dumps({'error':type(error).__name__,'frame_received':False})+'\n');return 1
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None,'LeRTX could not open the workspace',
            'The workspace could not be opened. Check that the NVIDIA driver is available and that the selected USD file is readable.\n\n'
            f'Diagnostic log: {path}\n\n{type(error).__name__}: {error}')
        return 1
