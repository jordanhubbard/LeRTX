"""Accessible role text with outlined color dots shared across desktop controls."""
import base64,html,re
from functools import lru_cache
from .arm_colors import role_color
from PySide6.QtCore import Qt,QBuffer,QByteArray,QIODevice,QSize,QTimer
from PySide6.QtGui import QColor,QIcon,QPainter,QPen,QPixmap
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


def role_html(text,profile,rich=False):
    def replace(match):
        return f'<img width="14" height="14" src="{dot_uri(role_color(profile,match[0].lower()))}"> '+match[0]
    # Preserve existing authored links/markup; never inspect or rewrite attributes.
    parts=re.split(r'(<[^>]*>)',text) if rich else [html.escape(text).replace('\n','<br>')]
    return ''.join(part if rich and part.startswith('<') else ROLES.sub(replace,part) for part in parts)


def role_icon(text,profile):
    roles=[m[0].lower() for m in ROLES.finditer(text)]
    if not roles:return QIcon()
    image=QPixmap(16*len(roles),16);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image)
    for i,role in enumerate(roles):painter.drawPixmap(i*16,0,dot(role_color(profile,role)))
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
            if ROLES.search(self.text()):self.setIcon(role_icon(self.text(),profile()));self._had_role=True
            elif getattr(self,'_had_role',False):self.setIcon(QIcon());self._had_role=False
    class RoleCheckBox(QCheckBox):
        def __init__(self,text='',parent=None):
            super().__init__(text,parent);self.refresh_role_colors()
        def refresh_role_colors(self):
            if ROLES.search(self.text()):
                self.setIcon(role_icon(self.text(),profile()))
                self.setIconSize(QSize(16*len(ROLES.findall(self.text())),16))
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
