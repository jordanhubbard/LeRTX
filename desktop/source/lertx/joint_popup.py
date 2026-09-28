"""Contextual simulated-joint controls; native work stays on the scene worker."""
import math


def build_joint_popup(viewport, owner, joint):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QFrame, QVBoxLayout, QLabel, QSlider, QDoubleSpinBox, QPushButton,
    )

    class JointPopup(QFrame):
        def __init__(self):
            super().__init__(owner, Qt.WindowType.Popup)
            self.joint = dict(joint)
            self.setObjectName('jointPopup')
            self.setFrameShape(QFrame.Shape.StyledPanel)
            self.setFixedWidth(320)
            layout = QVBoxLayout(self)
            title = f"{joint['role'].title()} · {joint['name'].replace('_', ' ').title()}"
            self.setAccessibleName(title)
            layout.addWidget(QLabel(title))
            layout.addWidget(QLabel('Move simulated joint'))
            self.gripper = joint['name'] == 'gripper'
            self.low = 0. if self.gripper else math.degrees(joint['low'])
            self.high = 100. if self.gripper else math.degrees(joint['high'])
            unit = '%' if self.gripper else '°'
            self.value = QDoubleSpinBox()
            self.value.setDecimals(2)
            self.value.setRange(self.low, self.high)
            self.value.setSuffix(' ' + unit)
            self.value.setSingleStep(1.)
            self.value.setKeyboardTracking(False)
            self.value.setAccessibleName(title + ' target')
            layout.addWidget(self.value)
            self.slider = QSlider(Qt.Orientation.Horizontal)
            self.slider.setRange(0, 1000)
            self.slider.setAccessibleName(title + ' target slider')
            layout.addWidget(self.slider)
            layout.addWidget(QLabel(f'Range: {self.low:.1f}{unit} to {self.high:.1f}{unit}'))
            self.note = QLabel('Simulation only · works while paused')
            self.note.setWordWrap(True)
            layout.addWidget(self.note)
            self.unlock = QPushButton('Manipulate follower independently')
            self.unlock.clicked.connect(self.unlock_follower)
            layout.addWidget(self.unlock)
            close = QPushButton('Done')
            close.clicked.connect(self.close)
            layout.addWidget(close)
            self.set_value(joint['value'])
            self.slider.valueChanged.connect(self.slide)
            self.value.valueChanged.connect(self.enter_value)
            self.set_locked(joint['locked'], joint.get('lock_reason'))

        def set_value(self, radians):
            fraction = (radians-joint['low'])/(joint['high']-joint['low'])
            self.slider.blockSignals(True)
            self.value.blockSignals(True)
            self.slider.setValue(round(1000*fraction))
            self.value.setValue(100*fraction if self.gripper else math.degrees(radians))
            self.slider.blockSignals(False)
            self.value.blockSignals(False)

        def submit(self, radians):
            if self.joint['locked'] or not owner._ready or viewport.popup is not self:
                return
            radians = max(joint['low'], min(joint['high'], radians))
            self.set_value(radians)
            viewport.intent = (joint['role'], joint['name'], radians)

        def slide(self, value):
            self.submit(joint['low']+(joint['high']-joint['low'])*value/1000)

        def enter_value(self, value):
            self.submit(joint['low']+(joint['high']-joint['low'])*value/100
                        if self.gripper else math.radians(value))

        def set_locked(self, locked, reason=None, can_unlock=None):
            self.joint['locked'] = locked
            self.slider.setEnabled(not locked)
            self.value.setEnabled(not locked)
            self.note.setText((reason or 'Disable following to manipulate the follower.')
                              if locked else 'Simulation only · works while paused')
            if can_unlock is None:
                can_unlock = joint['role'] == 'follower' and not getattr(
                    getattr(owner, 'robot_panel', None), 'state', {}).get('live_roles')
            self.unlock.setVisible(bool(locked and can_unlock))
            if locked and viewport.intent and viewport.intent[:2] == (joint['role'], joint['name']):
                viewport.intent = None

        def unlock_follower(self):
            owner.robot_panel.set_following(False)
            self.note.setText('Waiting for independent follower control…')

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape:
                viewport.cancel()
                event.accept()
            else:
                super().keyPressEvent(event)

        def hideEvent(self, event):
            if viewport.popup is self:
                viewport.popup = None
            super().hideEvent(event)
            self.deleteLater()

    return JointPopup()
