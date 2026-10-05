"""Setup-only explanations and Qt views of the shared native renderer's image."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy
from .robot import JOINT_NAMES

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


class JointMap(QWidget):
    """A deliberately schematic, numbered side view for finding unfamiliar joints."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = None
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
            color = QColor('#ffc36b' if selected else '#58d6b1' if name in self.confirmed else '#b1c2d6')
            p.setPen(QPen(color, 1.5))
            p.drawLine(QPointF(*point), QPointF(label[0]+16, label[1]-9))
            if name in self.moving:
                p.setPen(QPen(QColor('#58d6b1'), 3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(*point), 20, 20)
            p.setPen(QPen(color, 2))
            p.setBrush(QColor('#ffc36b' if selected else '#26384c'))
            p.drawEllipse(QPointF(*point), 13, 13)
            p.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
            p.setPen(QColor('#17202b') if selected else color)
            p.drawText(QRectF(point[0]-13, point[1]-13, 26, 26), Qt.AlignmentFlag.AlignCenter, str(i))
            p.setPen(color)
            p.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold if selected else QFont.Weight.Normal))
            p.drawText(QPointF(*label), text)
