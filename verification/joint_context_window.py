"""Qualify right-drag joint controls against actual Qt, RTX picking and physics.

Run under native_guard.py on Linux or a bounded Windows Job Object.
The filename is retained for existing runners; the former popup UI is obsolete.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'desktop/source'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    from lertx.ui import build_application, build_main_window
    app = build_application([])
    from PySide6.QtCore import QTimer, Qt, QPoint
    from PySide6.QtTest import QTest
    from lertx.config import DEFAULT_PROFILE
    from lertx.runtime import SceneWorker
    from lertx.scene import create_default_scene
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile['rendering'].update(width=640, height=360, target_fps=15)
    result = {'complete': False, 'physical_hardware_tested': False}
    state = {'phase': 'startup'}
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        scene = Path(directory)/'pair.usdc'
        create_default_scene(str(scene), include_robots=True)
        window = build_main_window(profile, lambda: SceneWorker(profile), str(scene),
                                   str(Path(directory)/'settings.json'))
        window.show()
        window.open_scene(str(scene))
        timer = QTimer(window)

        def finish(error=None):
            timer.stop()
            result.update(complete=error is None, seconds=round(time.monotonic()-started, 3))
            if error:
                result['error'] = str(error)
                result['phase'] = state['phase']
                result['native_status'] = window.native_status_label.text()
                result['ui_status'] = window.statusBar().currentMessage()
            window.viewport_label.cancel()
            window.has_unsaved_changes = False
            window.close()

        # Assertions in asynchronous worker callbacks otherwise become UI errors
        # and leave this verifier waiting until its outer deadline.
        show_error = window._show_error
        def failed(error):
            result['previous_ui_status'] = window.statusBar().currentMessage()
            result['selected_path'] = window._selected_path()
            show_error(error)
            finish(error)
        window._show_error = failed

        def picked(hit):
            assert hit, 'Native picker did not find a leader joint'
            u, v, joint = hit
            state.update(phase='motion', joint=joint)
            view = window.viewport_label
            left, top, width, height = view.image_rect()
            start = QPoint(round(left+u*width), round(top+v*height))
            # A 50-pixel horizontal gesture requests 25 degrees, bounded by limits.
            from lertx.joint_interaction import drag_target
            state['target'] = drag_target(joint['value'], 50, 0, joint['low'], joint['high'])
            state['before'] = window._image.copy()
            QTest.mousePress(view, Qt.MouseButton.RightButton, pos=start)
            QTest.mouseMove(view, start+QPoint(50, 0))
            QTest.mouseRelease(view, Qt.MouseButton.RightButton, pos=start+QPoint(50, 0))

        def inspect_motion():
            joint = state['joint']
            role, name = joint['role'], joint['name']
            target = window.worker.physics.targets[role][name]
            measured = window.worker.physics.robot_positions()[role][name]
            assert abs(target-state['target']) < 1e-6, (target, state['target'])
            assert abs(measured-joint['value']) > .005, (measured, joint['value'])
            assert not window.worker.clock.playing
            assert not window.worker.document.dirty
            return dict(target_radians=target, measured_radians=measured,
                        initial_radians=joint['value'], paused=True,
                        authored_scene_unchanged=True)

        def verified(value):
            result.update(value)
            assert window._image != state['before'], 'Rendered image did not change'
            assert window._selected_path(), 'Native pick did not synchronize selection'
            result.update(rendered_motion=True, selected_path=window._selected_path())
            window.grab().save(str(args.report.with_suffix('.png')))
            state['before_pan'] = window._image.copy()
            view = window.viewport_label
            QTest.mousePress(view, Qt.MouseButton.MiddleButton, pos=QPoint(200,150))
            QTest.mouseMove(view, QPoint(240,170))
            QTest.mouseRelease(view, Qt.MouseButton.MiddleButton, pos=QPoint(240,170))
            state['phase'] = 'pan'

        def tick():
            try:
                if time.monotonic()-started > 150:
                    raise AssertionError('Native direct-drag verification timed out: '+state['phase'])
                if window._pending or not window._ready:
                    return
                if state['phase'] == 'startup' and window._image is not None and window._idle_frame:
                    image = window._image
                    candidates = []
                    left, top, width, height = window.viewport_label.image_rect()
                    for y in range(8, image.height(), 12):
                        for x in range(8, image.width(), 12):
                            color = image.pixelColor(x,y)
                            if color.green() > color.red()*1.25 and color.green() > 60:
                                # Probe exactly the integer Qt point that the
                                # synthetic press will use after image scaling.
                                px = round(left+x/image.width()*width)
                                py = round(top+y/image.height()*height)
                                candidates.append(((px-left)/width, (py-top)/height))
                    def probe():
                        for u, v in candidates:
                            joint = window.worker.pick(u,v)['joint']
                            if joint and joint['role'] == 'leader' and joint['name'] != 'gripper':
                                return u, v, joint
                    state['phase'] = 'pick'
                    window._command(probe, picked)
                elif (state['phase'] == 'motion' and window.viewport_label.press is None
                      and window.viewport_label.intent is None and window._idle_frame):
                    state['phase'] = 'verify'
                    window._command(inspect_motion, verified)
                elif state['phase'] == 'pan' and window._idle_frame:
                    assert window._image != state['before_pan'], 'Middle-drag did not change rendered camera'
                    result['middle_drag_pan'] = True
                    finish()
            except Exception as error:
                finish(repr(error))

        timer.timeout.connect(tick)
        timer.start(40)
        app.exec()
        result['clean_shutdown'] = window.worker is None
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['complete'] and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
