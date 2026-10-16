"""Typed in-process development control; enabled with the diagnostic interface."""
import itertools
import weakref


class DevelopmentControl:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.targets = weakref.WeakValueDictionary()
        self.ids = weakref.WeakKeyDictionary()
        self.sequence = itertools.count(1)
        self.operations = itertools.count(1)

    def identify(self, target):
        if target not in self.ids:
            self.ids[target] = str(next(self.sequence))
        key = self.ids[target]
        self.targets[key] = target
        return key

    @staticmethod
    def actions(target):
        from PySide6.QtWidgets import (QAbstractButton, QLineEdit, QTextEdit,
            QPlainTextEdit, QComboBox, QAbstractSpinBox, QAbstractItemView,
            QTabWidget, QSlider, QWidget)
        from PySide6.QtGui import QAction
        result = []
        if isinstance(target, QAbstractButton):
            result += ['click', 'press', 'release']
            if target.isCheckable():result += ['set_checked']
        if isinstance(target, QAction):result += ['trigger']
        if isinstance(target, (QLineEdit, QTextEdit, QPlainTextEdit)):result += ['set_text']
        if isinstance(target, (QComboBox, QTabWidget)):result += ['select_index']
        if isinstance(target, (QAbstractSpinBox, QSlider)):result += ['set_value']
        if isinstance(target, QAbstractItemView):result += ['select_item', 'activate_item']
        if isinstance(target, QWidget):result += ['focus', 'close']
        return result

    def submit(self, payload):
        from PySide6.QtCore import QTimer
        if payload.get('command') == 'ui_action':
            if set(payload) - {'command', 'id', 'action', 'value'}:
                raise ValueError('Unknown UI fields')
            target = self.targets.get(payload.get('id'))
            if target is None:raise ValueError('Unknown or stale control id; refresh /ui')
            action = payload.get('action')
            if action not in self.actions(target):raise ValueError('Unsupported control action')
            work = lambda: self.interact(target, action, payload.get('value'))
        elif payload.get('command') == 'service':
            if set(payload) - {'command', 'name', 'role'}:raise ValueError('Unknown service fields')
            name = payload.get('name')
            if name not in self.catalog():raise ValueError('Unknown application service')
            if name in ('open_hardware', 'open_setup') and payload.get('role') not in ('leader', 'follower'):
                raise ValueError('A leader or follower role is required')
            work = lambda: self.service(name, payload.get('role'))
        else:raise ValueError('Unknown development command')
        operation = str(next(self.operations))
        def execute():
            try:
                result = work()
                self.diagnostics.record('control.completed', operation=operation, result=result)
            except Exception as exc:
                self.diagnostics.record('control.failed', operation=operation, error=str(exc))
        # A separate event-loop turn lets HTTP acknowledge before a nested modal loop.
        QTimer.singleShot(0, execute)
        self.diagnostics.record('control.queued', operation=operation)
        return {'queued': True, 'operation': operation}

    @staticmethod
    def catalog():
        return {'open_devices': {}, 'open_robot_session': {},
                'open_hardware': {'role': ['leader', 'follower']},
                'open_setup': {'role': ['leader', 'follower']}}

    def service(self, name, role):
        owner = self.diagnostics.owner
        if name == 'open_devices':owner._on_devices()
        elif name == 'open_robot_session':owner.open_robot_session()
        else:
            from pathlib import Path
            from .devices import RoleAssignments, scan_candidates
            roles = RoleAssignments(Path(owner.config_path).parent/'devices.json')
            candidates = scan_candidates()
            roles.update(candidates)
            state, candidate = roles.resolve(role, candidates)
            if state != 'assigned':raise ValueError('No uniquely assigned device for '+role)
            if name == 'open_hardware':
                if owner.open_hardware(candidate, role) is False:raise ValueError(owner.statusBar().currentMessage())
            else:owner.open_setup(role=role, candidate=candidate)
        return {'service': name}

    def interact(self, target, action, value):
        from PySide6.QtWidgets import QWidget, QTabWidget, QComboBox, QLineEdit, QAbstractItemView
        from PySide6.QtCore import Qt
        from shiboken6 import isValid
        if not isValid(target):raise ValueError('Control was destroyed; refresh /ui')
        if not target.isEnabled():raise ValueError('Control is disabled')
        if isinstance(target, QWidget) and not target.isVisible():raise ValueError('Control is hidden')
        if action in ('click', 'trigger', 'close'):
            getattr(target, action)()
        elif action in ('press', 'release'):
            target.setDown(action == 'press')
            getattr(target, 'pressed' if action == 'press' else 'released').emit()
        elif action == 'focus':target.setFocus()
        elif action == 'set_checked':
            if type(value) is not bool:raise ValueError('Expected boolean')
            if target.isChecked() != value:target.click()
        elif action == 'set_text':
            if not isinstance(value, str) or len(value) > 4096:raise ValueError('Expected bounded text')
            if target.isReadOnly():raise ValueError('Control is read-only')
            if isinstance(target, QLineEdit):target.setText(value)
            else:target.setPlainText(value)
        elif action == 'select_index':
            if type(value) is not int or not 0 <= value < target.count():raise ValueError('Invalid item index')
            target.setCurrentIndex(value)
            if isinstance(target, QComboBox):target.activated.emit(value)
        elif action == 'set_value':
            import math
            if type(value) not in (int, float) or not math.isfinite(value) or not target.minimum() <= value <= target.maximum():
                raise ValueError('Value outside control range')
            target.setValue(value)
        elif action in ('select_item', 'activate_item'):
            if not isinstance(value, list) or not value or any(type(row) is not int or row < 0 for row in value):
                raise ValueError('Expected row path')
            from PySide6.QtCore import QModelIndex
            index = QModelIndex()
            model = target.model()
            for row in value:index = model.index(row, 0, index)
            if not index.isValid() or not model.flags(index) & Qt.ItemFlag.ItemIsEnabled:raise ValueError('Invalid tree/list item')
            target.setCurrentIndex(index)
            target.scrollTo(index)
            if action == 'activate_item':target.activated.emit(index)
        return {'id': self.identify(target), 'action': action}
