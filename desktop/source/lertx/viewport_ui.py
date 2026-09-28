"""Qt pointer gestures; native commands stay on the scene worker."""
from .joint_interaction import image_coordinates, drag_target


def build_viewport(owner):
    from PySide6.QtCore import Qt, QEvent
    from PySide6.QtWidgets import QLabel, QApplication

    class Viewport(QLabel):
        def __init__(self):
            super().__init__()
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.generation = 0
            self.popup = None
            self.cancel()
            QApplication.instance().installEventFilter(self)

        def cancel(self):
            self.generation += 1
            if self.popup is not None:
                popup, self.popup = self.popup, None
                popup.close()
            self.press = self.last = None
            self.button = None
            self.context_pending = False
            self.context_dragged = False
            self.joint = None
            self.intent = None
            self.mode = None
            self.released = False
            self.pick_pending = False
            self.dragged = False
            self.unsetCursor()

        def eventFilter(self, watched, event):
            if (event.type() == QEvent.Type.ApplicationDeactivate or
                    (watched is owner and event.type() == QEvent.Type.WindowDeactivate
                     and self.popup is None)):
                self.cancel()
            return False

        def open_joint_control(self, position, global_position):
            if not owner._ready:
                return
            self.cancel()
            uv = image_coordinates(position.x(), position.y(), self.image_rect())
            if uv is None:
                return
            self.context_pending = True
            generation = self.generation

            def picked(result):
                if generation != self.generation or not owner._ready:
                    return
                self.context_pending = False
                item = owner._tree_items.get(result['path'])
                if item:
                    owner.search_edit.clear()
                    owner.tree.setCurrentItem(item)
                    owner.tree.scrollToItem(item)
                else:
                    owner.tree.clearSelection()
                joint = result['joint']
                if not joint:
                    owner.statusBar().showMessage('Right-click a movable arm link to control its joint.')
                    return
                from .joint_popup import build_joint_popup
                self.popup = popup = build_joint_popup(self, owner, joint)
                popup.adjustSize()
                screen = QApplication.screenAt(global_position) or self.screen()
                area = screen.availableGeometry()
                popup.move(max(area.left(), min(global_position.x(), area.right()-popup.width()+1)),
                           max(area.top(), min(global_position.y(), area.bottom()-popup.height()+1)))
                popup.show()
                popup.slider.setFocus()

            owner._command(lambda: owner.worker.pick(*uv), picked)

        def update_joint_state(self, state):
            if self.popup is None:
                return
            if not state or not state.get('positions'):
                self.cancel()
                return
            live = bool(state.get('live_roles'))
            follower = self.popup.joint['role'] == 'follower'
            self.popup.set_locked(live or (follower and state['following']),
                'Disable physical live view before simulated manipulation.' if live else
                'Disable following to manipulate the follower.', can_unlock=follower and not live)

        def contextMenuEvent(self, event):
            # Mouse context events arrive on press on some platforms, release on
            # others. The matched right release below owns that gesture. Native
            # trackpad/keyboard context events can also arrive without a press.
            if self.context_dragged:
                self.context_dragged = False
            elif self.press is None and not self.context_pending and self.popup is None:
                position = event.pos() if event.pos().x() >= 0 else self.rect().center()
                self.open_joint_control(position, self.mapToGlobal(position))
            event.accept()

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
            if event.button() == Qt.MouseButton.RightButton:
                self.mode = 'context'
            elif event.button() == Qt.MouseButton.MiddleButton:
                self.mode = 'pan'
            elif event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self.mode = 'orbit'
            elif event.button() == Qt.MouseButton.LeftButton:
                uv = image_coordinates(self.press.x(), self.press.y(), self.image_rect())
                if uv is None:
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
                        owner.statusBar().showMessage(self.joint.get('lock_reason','Disable following in Robot Controls before dragging the follower.'))
                        self.joint = None
                    elif self.joint:
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self.update_intent()
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
            elif self.mode == 'context':
                if (self.last-self.press).manhattanLength() >= QApplication.startDragDistance():
                    self.dragged = True
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
            if self.mode == 'context':
                if not self.dragged and (self.last-self.press).manhattanLength() < QApplication.startDragDistance():
                    self.open_joint_control(event.position(), event.globalPosition().toPoint())
                else:
                    self.cancel()
                    self.context_dragged = True
            elif self.mode == 'joint':
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
