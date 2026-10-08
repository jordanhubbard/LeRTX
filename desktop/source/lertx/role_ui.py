"""Accessible role text with contrast-aware role symbol badges shared across desktop controls."""
import base64,html,re
from functools import lru_cache
from .arm_colors import role_color
from PySide6.QtCore import Qt,QBuffer,QByteArray,QIODevice,QSize,QTimer
from PySide6.QtGui import QColor,QIcon,QPainter,QPen,QPixmap,QPainterPath
from PySide6.QtWidgets import QLabel,QPushButton,QCheckBox,QStatusBar

ROLES=re.compile(r'\b(leader|follower)\b',re.I)


@lru_cache(maxsize=64)
def dot(color):
    pixmap=QPixmap(16,16);pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#151515'),2));painter.setBrush(QColor('#ffffff'))
    painter.drawEllipse(1,1,14,14)
    painter.setPen(QPen(QColor('#ffffff'),1));painter.setBrush(QColor(color))
    painter.drawEllipse(3,3,10,10);painter.end()
    return pixmap


@lru_cache(maxsize=64)
def dot_uri(color):
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    dot(color).save(buffer,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(bytes(data)).decode('ascii')


def badge_ink(color):
    c=QColor(color)
    linear=lambda v:v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    luminance=sum(w*linear(v) for w,v in zip((.2126,.7152,.0722),(c.redF(),c.greenF(),c.blueF())))
    return '#000000' if luminance>.179 else '#ffffff'


@lru_cache(maxsize=128)
def badge(role,color):
    pixmap=QPixmap(24,24);pixmap.fill(Qt.GlobalColor.transparent)
    p=QPainter(pixmap);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#151515'),2));p.setBrush(QColor('#ffffff'));p.drawEllipse(1,1,22,22)
    p.setPen(QPen(QColor('#ffffff'),1));p.setBrush(QColor(color));p.drawEllipse(3,3,18,18)
    ink=QColor(badge_ink(color));p.setPen(QPen(ink,1.6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if role=='leader':
        path=QPainterPath();path.moveTo(6,15)
        for x,y in ((7.5,9),(10,8),(14,8),(16.5,9),(18,15),(16,16),(14,13),(10,13),(8,16),(6,15)):path.lineTo(x,y)
        p.drawPath(path);p.drawLine(8,10,10,10);p.drawLine(9,9,9,11)
        p.setBrush(ink);p.drawEllipse(14,9,1.5,1.5)
    else:
        p.drawLine(12,6,12,10);p.drawLine(6,10,18,10)
        for side in (-1,1):
            path=QPainterPath();path.moveTo(12+side*6,10);path.lineTo(12+side*6,14)
            path.lineTo(12+side*3,17);path.lineTo(12+side*3,14);p.drawPath(path)
    p.end();return pixmap


@lru_cache(maxsize=128)
def badge_uri(role,color):
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    badge(role,color).save(buffer,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(bytes(data)).decode('ascii')


def role_html(text,profile,rich=False):
    def replace(match):
        role=match[0].lower()
        return f'<img width="20" height="20" src="{badge_uri(role,role_color(profile,role))}"> '+match[0]
    # Preserve existing authored links/markup; never inspect or rewrite attributes.
    parts=re.split(r'(<[^>]*>)',text) if rich else [html.escape(text).replace('\n','<br>')]
    return ''.join(part if rich and part.startswith('<') else ROLES.sub(replace,part) for part in parts)


def role_icon(text,profile):
    roles=[m[0].lower() for m in ROLES.finditer(text)]
    if not roles:return QIcon()
    image=QPixmap(24*len(roles),24);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image)
    for i,role in enumerate(roles):painter.drawPixmap(i*24,0,badge(role,role_color(profile,role)))
    painter.end();icon=QIcon()
    for mode in (QIcon.Mode.Normal,QIcon.Mode.Disabled,QIcon.Mode.Active,QIcon.Mode.Selected):
        icon.addPixmap(image,mode)
    return icon


def widgets(profile):
    """Use a getter so already-open windows follow committed palette changes."""
    class RoleLabel(QLabel):
        def __init__(self,text='',parent=None):
            super().__init__(parent)
            self._role_text='';self._role_format=Qt.TextFormat.AutoText
            self.setText(text)
        def text(self):return self._role_text
        def setText(self,text):
            self._role_text=text;self.refresh_role_colors()
        def clear(self):self.setText('')
        def setTextFormat(self,format):
            self._role_format=format;self.refresh_role_colors()
        def refresh_role_colors(self):
            text=self._role_text
            if ROLES.search(text):
                rich=self._role_format==Qt.TextFormat.RichText or (
                    self._role_format==Qt.TextFormat.AutoText and bool(re.search(r'<(?:b|br|a|span|img)\b',text)))
                super().setTextFormat(Qt.TextFormat.RichText)
                super().setText(role_html(text,profile(),rich))
                self.setAccessibleName(re.sub('<[^>]+>','',text))
            else:
                super().setTextFormat(self._role_format);super().setText(text)
                self.setAccessibleName(re.sub('<[^>]+>','',text))
    class RoleButton(QPushButton):
        def __init__(self,text='',parent=None):
            super().__init__(text,parent);self.refresh_role_colors()
        def setText(self,text):
            super().setText(text);self.refresh_role_colors()
        def refresh_role_colors(self):
            if ROLES.search(self.text()):
                self.setIcon(role_icon(self.text(),profile()));self.setIconSize(QSize(20*len(ROLES.findall(self.text())),20));self._had_role=True
            elif getattr(self,'_had_role',False):self.setIcon(QIcon());self._had_role=False
    class RoleCheckBox(QCheckBox):
        def __init__(self,text='',parent=None):
            super().__init__(text,parent);self.refresh_role_colors()
        def refresh_role_colors(self):
            if ROLES.search(self.text()):
                self.setIcon(role_icon(self.text(),profile()))
                self.setIconSize(QSize(20*len(ROLES.findall(self.text())),20))
    return RoleLabel,RoleButton,RoleCheckBox


def status_bar(profile):
    Label,_,_=widgets(profile)
    class RoleStatusBar(QStatusBar):
        def __init__(self):
            super().__init__();self.label=Label();self.addWidget(self.label,1)
            self.expiry=QTimer(self);self.expiry.setSingleShot(True);self.expiry.timeout.connect(self.clearMessage)
        def showMessage(self,text,timeout=0):
            self.expiry.stop();self.label.setText(text);self.messageChanged.emit(text)
            if timeout:self.expiry.start(timeout)
        def currentMessage(self):return self.label.text()
        def clearMessage(self):self.showMessage('')
    return RoleStatusBar()
