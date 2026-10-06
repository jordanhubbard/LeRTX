"""Setup-only explanations and Qt views of the shared native renderer's image."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from .robot import JOINT_NAMES
from .arm_colors import role_color, ROLE_NAMES, DEFAULT_COLORS

# User-facing names describe the part before introducing the robot terminology.
JOINT_GUIDES = {
    'shoulder_pan': ('Base turn', 'Shoulder pan',
        'Find the rotating platform directly above the table clamp. Hold the upright '
        'part above it and turn the whole arm gently left, then right.'),
    'shoulder_lift': ('Upper-arm hinge', 'Shoulder lift',
        'Find the lowest sideways hinge, just above the rotating base. Support the '
        'long link rising from it. Tip that link forward and backward at this hinge.'),
    'elbow_flex': ('Middle hinge', 'Elbow flex',
        'Follow the first long link up from the base. The hinge at its far end is '
        'the elbow. Hold the first link still and fold, then straighten the next link.'),
    'wrist_flex': ('Wrist tilt', 'Wrist flex',
        'Follow the second long link toward the hand. At its end, bend the entire '
        'hand up and down, like nodding. Keep the middle hinge still.'),
    'wrist_roll': ('Wrist twist', 'Wrist roll',
        'Find the rotating section immediately behind the hand. Twist the hand '
        'around its length, like turning a doorknob. Do not wind the cable around it.'),
    'gripper': ('Claw / trigger', 'Gripper',
        'Follower: gently open and close the two fingers by hand. Leader: squeeze '
        'and release the small trigger at the handle. Do not force either mechanism.'),
}


class NativeSetupView(QWidget):
    """Display the same OVRTX image as the workspace; never create another renderer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setMinimumSize(320, 210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName('Live 3D calibration preview')

    def set_image(self, image):
        self.image = image
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#101720'))
        if self.image is None:
            p.setPen(QColor('#c4d0df'))
            p.drawText(self.rect().adjusted(24, 24, -24, -24),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       'The 3D arm will appear here when the reference pose is ready.')
            return
        size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF((self.width()-size.width())/2, (self.height()-size.height())/2,
                        size.width(), size.height())
        p.drawImage(target, self.image)


class SetupPreviewWindow(QDialog):
    """A dedicated solid RTX view, fed by the application's native frame stream.

    The native owner still serializes every renderer call and pose publication.
    A second Qt window does not require a second competing GPU scene owner.
    """
    def __init__(self, owner):
        super().__init__(owner)
        from .role_ui import widgets
        QLabel,_,_=widgets(lambda:owner.profile)
        self.owner = owner
        self.role = 'follower'
        self.mode = 'waiting'
        self.disposed = False
        self.setWindowTitle('Live arm · NVIDIA RTX')
        self.resize(900, 700)
        self.setMinimumSize(480, 400)
        self.setModal(False)
        layout = QVBoxLayout(self)
        self.identity = QLabel()
        self.identity.setWordWrap(True)
        layout.addWidget(self.identity)
        self.mode_label=QLabel('Waiting for setup · not mirroring physical motion')
        self.mode_label.setWordWrap(True)
        self.mode_label.setStyleSheet('font-size: 16px; font-weight: bold; padding: 8px; border: 1px solid #8e949b;')
        layout.addWidget(self.mode_label)
        self.legend = QLabel()
        layout.addWidget(self.legend)
        self.heading = QLabel('SO-101 · live 3D arm')
        self.heading.setWordWrap(True)
        self.heading.setStyleSheet('font-size: 20px; font-weight: bold;')
        layout.addWidget(self.heading)
        self.view = NativeSetupView(self)
        layout.addWidget(self.view, 1)
        self.status = QLabel('Waiting for the reference pose. Capture it to start measured motion.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        layout.addLayout(row)
        for title, kwargs in [('Turn left', {'orbit':(-.25,0)}),
                              ('Turn right', {'orbit':(.25,0)}),
                              ('Closer', {'zoom':-.2}), ('Farther', {'zoom':.2})]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, k=kwargs:self.camera(k))
            row.addWidget(button)
        fit = QPushButton('Frame arm')
        fit.clicked.connect(lambda:self.camera(None))
        row.addWidget(fit)
        owner.native_frame_ready.connect(self.view.set_image)

    def set_role(self, role):
        self.role = role
        color = role_color(self.owner.profile, role)
        self.set_mode(self.mode)
        from .role_ui import role_icon
        self.setWindowIcon(role_icon(role,self.owner.profile))
        self.identity.setText('Selected: '+ROLE_NAMES[role])
        self.identity.setStyleSheet(f'border-left: 12px solid {color}; padding: 8px; font-weight: bold;')
        self.legend.setText(' · '.join(
            r.capitalize()+(' (selected)' if r==role else ' (other arm)')
            for r in ('leader','follower')))

    def set_mode(self,mode):
        self.mode=mode
        title,message={
            'waiting':('RTX preview waiting','Waiting for setup · not mirroring physical motion'),
            'reference':('RTX reference guide','REFERENCE GUIDE · stationary pose to copy. Live mirroring starts after reference capture.'),
            'live':('live NVIDIA RTX view','LIVE · following measured joint motion'),
            'paused':('RTX view paused','PAUSED · not following physical motion'),
            'stale':('RTX view stopped','STOPPED · waiting for fresh physical readings'),
        }[mode]
        self.setWindowTitle(self.role.capitalize()+' · '+title)
        self.mode_label.setText(message)
        self.view.setAccessibleName(message)

    def camera(self, kwargs):
        if not self.owner._ready or self.owner.worker is None:
            return
        def work():
            if kwargs is None:
                from .robot import ROOTS
                self.owner.worker.frame_selection(ROOTS[self.role])
            else:
                self.owner.worker.move_camera(**kwargs)
            return self.owner.worker.tick(0.)
        self.owner._command(work, self.owner._accept_frame)

    def dispose(self):
        if self.disposed:
            return
        self.disposed = True
        self.owner.native_frame_ready.disconnect(self.view.set_image)
        self.close()
        self.deleteLater()


class JointMap(QWidget):
    """A deliberately schematic, numbered side view for finding unfamiliar joints."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = None
        self.role_color = DEFAULT_COLORS['follower']
        self.moving = set()
        self.confirmed = set()
        self.setMinimumHeight(205)
        self.setMaximumHeight(245)
        self.setAccessibleName('Arm joint location diagram, numbered from base to hand')

    def set_state(self, active=None, moving=(), confirmed=()):
        self.active, self.moving, self.confirmed = active, set(moving), set(confirmed)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#182331'))
        scale=min(self.width()/560,self.height()/225)
        p.translate((self.width()-560*scale)/2,(self.height()-225*scale)/2)
        p.scale(scale,scale)
        points = [(85, 177), (85, 143), (192, 58), (310, 95), (365, 95), (430, 95)]
        labels = [(12, 212), (10, 107), (138, 24), (245, 174), (347, 37), (437, 154)]
        short = ['Base turn', 'Upper-arm hinge', 'Middle hinge', 'Wrist tilt', 'Wrist twist', 'Claw / trigger']
        p.setPen(QPen(QColor('#73859a'), 13, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in zip(points, points[1:]):
            p.drawLine(QPointF(*a), QPointF(*b))
        p.drawLine(53, 191, 117, 191)
        p.setPen(QPen(QColor('#9aaec2'), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(430, 95, 463, 76)
        p.drawLine(463, 76, 478, 88)
        p.drawLine(430, 95, 463, 114)
        p.drawLine(463, 114, 478, 102)
        for i, (name, point, label, text) in enumerate(zip(JOINT_NAMES, points, labels, short), 1):
            selected = name == self.active
            color = QColor(self.role_color if selected else '#58d6b1' if name in self.confirmed else '#b1c2d6')
            p.setPen(QPen(color, 1.5))
            p.drawLine(QPointF(*point), QPointF(label[0]+16, label[1]-9))
            if name in self.moving:
                p.setPen(QPen(QColor('#58d6b1'), 3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(*point), 20, 20)
            p.setPen(QPen(color, 2))
            p.setBrush(QColor(self.role_color if selected else '#26384c'))
            p.drawEllipse(QPointF(*point), 13, 13)
            p.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
            p.setPen(QColor('white' if color.lightnessF()<.5 else '#17202b') if selected else color)
            p.drawText(QRectF(point[0]-13, point[1]-13, 26, 26), Qt.AlignmentFlag.AlignCenter, str(i))
            p.setPen(color)
            p.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold if selected else QFont.Weight.Normal))
            p.drawText(QPointF(*label), text)
