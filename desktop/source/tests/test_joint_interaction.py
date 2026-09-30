import math
import unittest
from lertx.joint_interaction import image_coordinates, drag_target


class JointMathTests(unittest.TestCase):
    def test_letterbox_and_limits(self):
        self.assertIsNone(image_coordinates(50, 9, (0, 10, 100, 50)))
        self.assertIsNone(image_coordinates(100, 35, (0, 10, 100, 50)))
        self.assertEqual(image_coordinates(50, 35, (0, 10, 100, 50)), (.5, .5))
        self.assertEqual(drag_target(0, 10000, 0, -1, 1), 1)
        self.assertEqual(drag_target(0, -10000, 0, -1, 1), -1)
        self.assertAlmostEqual(drag_target(.1, 10, 0, -1, 1), .1+math.radians(5))
        with self.assertRaises(ValueError): drag_target(0, float('nan'), 0, -1, 1)


class JointPointerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lertx.ui import build_application
        cls.app = build_application([])

    def setUp(self):
        from PySide6.QtWidgets import QMainWindow, QTreeWidget, QLineEdit
        from PySide6.QtGui import QPixmap
        from lertx.viewport_ui import build_viewport
        from types import SimpleNamespace
        self.owner = QMainWindow()
        owner = self.owner
        owner._ready = True; owner._pending = []; owner._tree_items = {}
        owner.tree = QTreeWidget(); owner.search_edit = QLineEdit()
        owner._display_image = lambda: None
        owner._accept_frame = lambda f: None
        owner._camera = lambda **kw: self.camera.append(kw)
        self.commands = []; self.camera = []
        self.joint = dict(role='leader', name='shoulder_pan', value=0., low=-1., high=1., locked=False)
        owner.worker = SimpleNamespace(pick=lambda *uv: dict(path=None, joint=self.joint),
            drag_joint=lambda *args, **kwargs: self.commands.append(args))
        owner._command = lambda fn, callback=None: owner._pending.append((fn, callback))
        self.view = build_viewport(owner); self.view.resize(400, 300)
        self.view.setPixmap(QPixmap(400, 300))

    def tearDown(self):
        self.view.cancel()
        self.view.deleteLater(); self.owner.deleteLater(); self.app.processEvents()

    def drain(self):
        while self.owner._pending:
            fn, callback = self.owner._pending.pop(0)
            result = fn()
            if callback: callback(result)

    def event(self, kind, x, y, modifiers=None, mouse_button=None):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        types = {'press':QEvent.Type.MouseButtonPress, 'move':QEvent.Type.MouseMove, 'release':QEvent.Type.MouseButtonRelease}
        selected = mouse_button or Qt.MouseButton.LeftButton
        button = Qt.MouseButton.NoButton if kind == 'move' else selected
        buttons = Qt.MouseButton.NoButton if kind == 'release' else selected
        event = QMouseEvent(types[kind], QPointF(x,y), QPointF(x,y), button, buttons, modifiers or Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view, event)

    def test_release_before_pick_finishes_preserves_final_target(self):
        self.event('press',100,100)
        for x in range(110,201,10): self.event('move',x,100)
        self.event('release',200,100)
        self.assertEqual(len(self.owner._pending),1)
        self.drain(); self.view.flush(); self.drain()
        self.assertEqual(len(self.commands),1)
        self.assertAlmostEqual(self.commands[0][2],math.radians(50))
        self.assertIsNone(self.view.press)

    def test_cancel_discards_delayed_pick_and_no_hit_allows_next_gesture(self):
        self.event('press',100,100); self.view.cancel(); self.drain()
        self.view.flush(); self.assertEqual(self.commands,[])
        self.joint = None
        self.event('press',100,100); self.drain(); self.event('release',100,100)
        self.assertIsNone(self.view.press)

    def test_locked_follower_and_camera_never_command_joint(self):
        from PySide6.QtCore import Qt
        self.joint.update(role='follower',locked=True)
        self.event('press',100,100); self.drain()
        self.event('move',200,100); self.event('release',200,100); self.view.flush()
        self.assertEqual(self.commands,[])
        self.assertIn('Disable following',self.owner.statusBar().currentMessage())
        self.event('press',100,100,Qt.KeyboardModifier.AltModifier)
        self.event('move',200,100); self.event('release',200,100)
        self.assertEqual(len(self.camera),1); self.assertEqual(self.owner._pending,[])

    def test_drag_back_to_origin_and_cancel_queued_intent(self):
        self.event('press',100,100); self.drain()
        self.event('move',200,100); self.view.flush(); self.drain()
        self.event('release',100,100); self.view.flush(); self.drain()
        self.assertEqual(self.commands[-1][2],0.)
        self.event('press',100,100); self.drain(); self.event('move',200,100)
        self.view.cancel(); self.view.flush()
        self.assertEqual(len(self.commands),2)

    def right_click(self):
        from PySide6.QtCore import Qt
        self.event('press', 100, 100, mouse_button=Qt.MouseButton.RightButton)
        self.event('release', 100, 100, mouse_button=Qt.MouseButton.RightButton)

    def test_right_drag_moves_the_joint_exactly_like_left_drag(self):
        from PySide6.QtCore import Qt
        self.event('press', 100, 100, mouse_button=Qt.MouseButton.RightButton)
        for x in range(110, 201, 10):
            self.event('move', x, 100, mouse_button=Qt.MouseButton.RightButton)
        self.event('release', 200, 100, mouse_button=Qt.MouseButton.RightButton)
        self.assertEqual(len(self.owner._pending), 1)
        self.drain(); self.view.flush(); self.drain()
        self.assertEqual(len(self.commands), 1)
        self.assertAlmostEqual(self.commands[0][2], math.radians(50))
        self.assertIsNone(self.view.press)

    def test_right_click_without_drag_selects_but_commands_nothing(self):
        self.right_click(); self.drain()
        self.assertEqual(self.commands, [])
        self.assertIsNone(self.view.press)

    def test_middle_drag_only_pans(self):
        from PySide6.QtCore import Qt
        self.event('press', 100, 100, mouse_button=Qt.MouseButton.MiddleButton)
        self.event('move', 180, 100, mouse_button=Qt.MouseButton.MiddleButton)
        self.event('release', 180, 100, mouse_button=Qt.MouseButton.MiddleButton)
        self.assertEqual(len(self.camera), 1)
        self.assertIn('pan', self.camera[0])
        self.assertEqual(self.owner._pending, [])
        self.assertEqual(self.commands, [])

    def test_letterbox_click_reports_status_and_queues_no_pick(self):
        from PySide6.QtGui import QPixmap
        self.view.setPixmap(QPixmap(200, 100))  # smaller than the 400x300 view: a letterboxed margin exists
        self.event('press', 0, 0)
        self.event('release', 0, 0)
        self.assertEqual(self.owner._pending, [])
        self.assertIn('outside the rendered image', self.owner.statusBar().currentMessage())

    def test_click_with_no_joint_hit_reports_status_and_stays_idle(self):
        self.joint = None
        self.event('press', 100, 100); self.drain()
        self.event('release', 100, 100)
        self.assertIsNone(self.view.press)
        self.assertIn('no movable joint', self.owner.statusBar().currentMessage())
        self.assertEqual(self.commands, [])

    def test_application_deactivate_discards_unsent_drag(self):
        from PySide6.QtCore import QEvent
        self.event('press', 100, 100); self.drain()
        self.event('move', 200, 100)
        self.app.sendEvent(self.owner, QEvent(QEvent.Type.ApplicationDeactivate))
        self.view.flush(); self.drain()
        self.assertIsNone(self.view.press)
        self.assertEqual(self.commands, [])

    def test_trackpad_pixel_scroll_zooms_without_joint_input(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        event = QWheelEvent(QPointF(100,100), QPointF(100,100), QPoint(0,24), QPoint(),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        self.app.sendEvent(self.view, event)
        self.assertEqual(self.camera, [{'zoom': -.02}])
        self.assertEqual(self.commands, [])


class JointRuntimeTests(unittest.TestCase):
    def test_paused_preview_is_bounded_and_playing_uses_elapsed_time(self):
        import copy
        from unittest.mock import Mock
        from lertx.runtime import SceneWorker
        from lertx.config import DEFAULT_PROFILE
        worker=SceneWorker(copy.deepcopy(DEFAULT_PROFILE))
        worker.physics=Mock();worker.publish_transforms=Mock()
        worker.tick=Mock(return_value={})
        worker.drag_joint('leader','shoulder_pan',.2,elapsed=100)
        self.assertEqual(worker.physics.step.call_count,4)
        self.assertFalse(worker.clock.playing)
        self.assertAlmostEqual(worker.clock.sim_time,4*worker.clock.dt)
        worker.tick.assert_called_with(0.)
        worker.physics.step.reset_mock();worker.clock.play()
        worker.drag_joint('leader','shoulder_pan',.3,elapsed=.03)
        worker.physics.step.assert_not_called()
        worker.tick.assert_called_with(.03)
