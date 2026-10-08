"""Application identity shared by the native entry point, windows and installer."""
from pathlib import Path
VERSION = "1.1.0"
APP_ID='org.lertx.LeRTX'
RESOURCES=Path(__file__).with_name('resources')


def configure_application(app):
    from PySide6.QtGui import QIcon
    app.setApplicationName('LeRTX')
    app.setApplicationDisplayName('LeRTX')
    app.setOrganizationName('LeRTX')
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName('org.lertx.LeRTX')
    app.setWindowIcon(QIcon(str(RESOURCES/'branding/lertx.svg')))
    import sys
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
