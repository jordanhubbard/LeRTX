"""Qt pointer gestures; native commands stay on the scene worker."""
from .joint_interaction import image_coordinates, drag_target


def build_viewport(owner):
    from PySide6.QtCore import Qt, QEvent
    from PySide6.QtWidgets import QLabel, QApplication, QToolTip
    from .role_ui import role_html

    class Viewport(QLabel):
        def __init__(self):
            super().__init__()
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.generation = 0
            self.cancel()
            QApplication.instance().installEventFilter(self)

        def cancel(self):
            self.generation += 1
            self.press = self.last = None
            self.button = None
            self.joint = None
            self.intent = None
            self.object = None
            self.object_intent = None
            self.object_pending = False
            self.mode = None
            self.released = False
            self.pick_pending = False
            self.dragged = False
            self.unsetCursor()

        def eventFilter(self, watched, event):
            if (event.type() == QEvent.Type.ApplicationDeactivate or
                    (watched is owner and event.type() == QEvent.Type.WindowDeactivate)):
                self.cancel()
            return False

        def image_rect(self):
            pixmap = self.pixmap()
            if pixmap is None or pixmap.isNull():
                return (0, 0, 0, 0)
            size = pixmap.deviceIndependentSize()
            rect = self.contentsRect()
            return (rect.x()+(rect.width()-size.width())/2,
                    rect.y()+(rect.height()-size.height())/2, size.width(), size.height())

        def mousePressEvent(self, event):
            if not owner._ready or self.press is not None:
                return
            self.cancel()
            self.setFocus()
            self.press = self.last = event.position()
            self.button = event.button()
            if event.button() == Qt.MouseButton.MiddleButton:
                self.mode = 'pan'
            elif event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self.mode = 'orbit'
            elif event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
                uv = image_coordinates(self.press.x(), self.press.y(), self.image_rect())
                if uv is None:
                    owner.statusBar().showMessage(
                        'That click landed outside the rendered image. Click directly on an arm link.')
                    self.cancel(); return
                self.mode = 'grab'
                self.pick_pending = True
                generation = self.generation
                def picked(result):
                    if generation != self.generation or not owner._ready:
                        return
                    self.pick_pending = False
                    path = result['path']
                    item = owner._tree_items.get(path)
                    if item:
                        owner.search_edit.clear()
                        owner.tree.setCurrentItem(item)
                        owner.tree.scrollToItem(item)
                    else:
                        owner.tree.clearSelection()
                    self.joint = result['joint']
                    if self.joint and self.joint['locked']:
                        reason = self.joint.get('lock_reason','Disable following in Robot Controls before dragging the follower.')
                        owner.statusBar().showMessage(reason)
                        QToolTip.showText(self.mapToGlobal(self.press.toPoint()), role_html(reason,owner.profile), self)
                        self.joint = None
                    elif self.joint:
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self.update_intent()
                    elif path:
                        self.object_pending = True
                        def inspected(value):
                            if generation != self.generation or not owner._ready:
                                return
                            self.object_pending = False
                            if 'error' in value:
                                owner.statusBar().showMessage(value['error'])
                                QToolTip.showText(self.mapToGlobal(self.press.toPoint()), value['error'], self)
                            else:
                                self.object = dict(path=path, translation=value['translation'],
                                    rotation=value['rotation'], scale=value['scale'],
                                    camera_right=value['camera_right'], camera_up=value['camera_up'],
                                    distance=value['distance'])
                                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                                self.update_object_intent()
                            if self.released and self.intent is None and self.object_intent is None:
                                self.cancel()
                        def begin_drag():
                            try:
                                return dict(owner.worker.begin_object_drag(path))
                            except ValueError as exc:
                                return {'error': str(exc)}
                        owner._command(begin_drag, inspected)
                        return
                    else:
                        message = 'Nothing there to select or move.'
                        owner.statusBar().showMessage(message)
                        QToolTip.showText(self.mapToGlobal(self.press.toPoint()), message, self)
                    if self.released and self.intent is None and self.object_intent is None:
                        self.cancel()
                owner._command(lambda: owner.worker.pick(*uv), picked)
            else:
                self.cancel()

        def update_intent(self):
            if self.joint is None or self.press is None:
                return
            delta = self.last-self.press
            if not self.dragged and delta.manhattanLength() < QApplication.startDragDistance():
                return
            self.dragged = True
            joint = self.joint
            value = drag_target(joint['value'], delta.x(), delta.y(), joint['low'], joint['high'])
            self.intent = (joint['role'], joint['name'], value)
            import math
            owner.statusBar().showMessage(f"{joint['role'].title()} · {joint['name'].replace('_', ' ')}: {math.degrees(value):.1f}° target · simulated")

        def update_object_intent(self):
            if self.object is None or self.press is None:
                return
            delta = self.last-self.press
            if not self.dragged and delta.manhattanLength() < QApplication.startDragDistance():
                return
            self.dragged = True
            obj = self.object
            right, up = obj['camera_right'], obj['camera_up']
            factor = .002*obj['distance']
            translation = [obj['translation'][i] + (right[i]*delta.x() - up[i]*delta.y())*factor for i in range(3)]
            self.object_intent = (obj['path'], translation, obj['rotation'], obj['scale'])
            name = obj['path'].rsplit('/', 1)[-1]
            owner.statusBar().showMessage(f'Moving {name} · simulated')

        def flush(self):
            if owner._pending or not owner._ready:
                return
            if self.intent is not None:
                intent, self.intent = self.intent, None
                import time
                now = time.monotonic()
                elapsed = now-getattr(owner, '_last_tick_started', now)
                owner._last_tick_started = now
                generation = self.generation
                def accepted(frame):
                    if generation == self.generation:
                        owner._accept_frame(frame)
                owner._command(lambda: owner.worker.drag_joint(*intent, elapsed=elapsed), accepted)
                if self.released:
                    # Preserve this queued final value; discard only later gestures.
                    self.press = self.last = None
                    self.joint = None
                    self.mode = None
            elif self.object_intent is not None:
                intent, self.object_intent = self.object_intent, None
                released = self.released
                path, translation, rotation, scale = intent
                generation = self.generation
                def accepted(frame):
                    if generation != self.generation:
                        return
                    owner._accept_frame(frame)
                    target = translation
                    if frame.get('object_target') and frame['object_target'][0] == path:
                        target = frame['object_target'][1]
                    if released:
                        owner._command(lambda: owner.worker.edit(path, target, rotation, scale), owner._apply_status)
                owner._command(lambda: owner.worker.drag_object(path, translation, rotation, scale), accepted)
                if released:
                    self.press = self.last = None
                    self.object = None
                    self.mode = None

        def mouseMoveEvent(self, event):
            if self.press is None or self.released:
                return
            delta = event.position()-self.last
            self.last = event.position()
            if self.mode == 'grab':
                self.update_intent()
                self.update_object_intent()
            elif self.mode == 'orbit':
                owner._camera(orbit=(-delta.x()*.006, delta.y()*.006))
            elif self.mode == 'pan':
                owner._camera(pan=(-delta.x()*.002, delta.y()*.002))

        def mouseReleaseEvent(self, event):
            if self.press is None or event.button() != self.button:
                return
            self.last = event.position()
            self.released = True
            self.unsetCursor()
            if self.mode == 'grab':
                self.update_intent()
                self.update_object_intent()
                # The pick/inspect may still be in flight; its callback retains release.
                if (not self.pick_pending and not self.object_pending
                        and self.intent is None and self.object_intent is None):
                    self.cancel()
            else:
                self.cancel()

        def wheelEvent(self, event):
            if self.press is None:
                delta = event.pixelDelta().y() or event.angleDelta().y()
                owner._camera(zoom=-delta/1200)
                event.accept()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape:
                self.cancel()
            else:
                super().keyPressEvent(event)

        def resizeEvent(self, event):
            self.cancel()
            super().resizeEvent(event)
            owner._display_image()

    return Viewport()
