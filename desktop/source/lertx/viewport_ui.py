"""Qt pointer gestures; native commands stay on the scene worker."""
from .joint_interaction import image_coordinates, drag_target


def build_viewport(owner):
    from PySide6.QtCore import Qt, QEvent
    from PySide6.QtWidgets import QLabel, QApplication, QToolTip

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
                self.mode = 'joint'
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
                        QToolTip.showText(self.mapToGlobal(self.press.toPoint()), reason, self)
                        self.joint = None
                    elif self.joint:
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self.update_intent()
                    else:
                        message = 'That link has no movable joint. Click and drag an arm link to drive it.'
                        owner.statusBar().showMessage(message)
                        QToolTip.showText(self.mapToGlobal(self.press.toPoint()), message, self)
                    if self.released and self.intent is None:
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

        def flush(self):
            if self.intent is None or owner._pending or not owner._ready:
                return
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

        def mouseMoveEvent(self, event):
            if self.press is None or self.released:
                return
            delta = event.position()-self.last
            self.last = event.position()
            if self.mode == 'joint':
                self.update_intent()
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
            if self.mode == 'joint':
                self.update_intent()
                # The pick may still be in flight; its callback retains release.
                if not self.pick_pending and self.intent is None:
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
