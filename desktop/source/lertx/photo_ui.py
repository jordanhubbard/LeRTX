"""Photo preview and explicit upload. Qt is imported only when opening the dialog."""
import copy
import time

from .photo import MAX_IMAGE_BYTES, photo_profile
from urllib.parse import urlsplit


def build_photo_dialog(profile, probe, parent=None):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt, QTimer
    from PySide6.QtGui import QImage, QImageReader, QPainter, QPixmap
    from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QPushButton, QVBoxLayout, QLineEdit, QProgressBar, QComboBox

    class PhotoDialog(QDialog):
        def __init__(self):
            super().__init__(parent)
            self.setWindowTitle("Reconstruct workspace from photo")
            self.resize(700, 760)
            self.profile = copy.deepcopy(profile)
            self.image_bytes = None
            self.result_scene = None
            self.ticket = None
            layout = QVBoxLayout(self)
            self.destination = QLabel("Upload destination: " + profile["llm"]["endpoint"])
            self.destination.setTextFormat(Qt.TextFormat.PlainText)
            self.destination.setWordWrap(True)
            layout.addWidget(self.destination)
            self.quality=QComboBox()
            if urlsplit(profile['llm']['endpoint']).hostname=='openrouter.ai':
                self.quality.addItem('Detailed shape · GPT-6 Astra · high reasoning', 'detail')
                self.quality.addItem('Quick layout · GPT-5 Mini · coarse geometry', 'fast')
            self.quality.addItem('Use configured model · '+profile['llm']['model'], 'configured')
            layout.addWidget(self.quality)
            self.quality_note=QLabel();self.quality_note.setWordWrap(True);layout.addWidget(self.quality_note)
            self.quality.currentIndexChanged.connect(self.describe_quality);self.describe_quality()
            note = QLabel("Only the selected image is sent after you click Upload. Images are resized to at most "
                          "2048 pixels per side and re-encoded without source metadata. The key stays in memory. "
                          "The result is an unverified draft with estimated dimensions, not a collision-safe map.")
            note.setWordWrap(True)
            layout.addWidget(note)
            layout.addWidget(QLabel('API key for this request (kept in memory; not saved)'))
            self.key_input = QLineEdit(self.profile['llm']['api_key'])
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setPlaceholderText('Enter the key for the upload destination above')
            self.key_input.setAccessibleName('Photo reconstruction API key')
            layout.addWidget(self.key_input)
            self.preview = QLabel("Choose a PNG or JPEG (up to 8 MiB / 16 million pixels)")
            self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview.setMinimumHeight(200)
            layout.addWidget(self.preview)
            self.choose_button = QPushButton("Choose photo")
            self.choose_button.clicked.connect(self.choose_photo)
            layout.addWidget(self.choose_button)
            self.upload_button = QPushButton("Upload and Reconstruct")
            self.upload_button.setEnabled(False)
            self.upload_button.clicked.connect(self.upload)
            layout.addWidget(self.upload_button)
            self.review_button=QPushButton('Open generated draft in the viewport')
            self.focus_label=QLabel('Initial view: choose a subject or show the whole scene')
            self.focus_choice=QComboBox();self.focus_label.hide();self.focus_choice.hide()
            layout.addWidget(self.focus_label);layout.addWidget(self.focus_choice)
            self.review_button.clicked.connect(self.open_draft);self.review_button.hide();layout.addWidget(self.review_button)
            self.status = QLabel("")
            self.status.setWordWrap(True)
            self.status.setStyleSheet('font-weight: bold; padding: 8px;')
            layout.addWidget(self.status)
            self.progress = QProgressBar();self.progress.setRange(0,0);self.progress.hide()
            layout.addWidget(self.progress)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(self.reject)
            layout.addWidget(cancel)
            self.timer = QTimer(self)
            self.timer.setInterval(40)
            self.timer.timeout.connect(self.poll)
            self.finished.connect(self.invalidate)

        def open_draft(self):
            if self.result_scene is not None:
                self.result_scene['focus_id']=self.focus_choice.currentData()
                self.accept()

        def describe_quality(self,*_):
            q=self.quality.currentData()
            self.quality_note.setText('Detailed shape uses high reasoning and a larger output budget. Allow several minutes and a higher API charge (the turtle trial took 5½ minutes and about $1.14). Results remain approximate colored meshes; textures and unseen surfaces are not recovered.' if q=='detail' else
                'Quick layout prioritizes speed and cost. Curved shapes may be very coarse.' if q=='fast' else
                'Uses the model and token budget from Settings. A vision-capable model with enough output tokens is required.')

        def choose_photo(self):
            path, _ = QFileDialog.getOpenFileName(self, "Choose workspace photo", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                self.select_photo(path)

        def select_photo(self, path):
            self.image_bytes = None
            self.result_scene=None;self.review_button.hide();self.focus_choice.hide();self.focus_label.hide()
            self.upload_button.setEnabled(False)
            self.preview.clear()
            try:
                with open(path, "rb") as stream:
                    raw = stream.read(MAX_IMAGE_BYTES+1)
                if len(raw) > MAX_IMAGE_BYTES:
                    raise ValueError()
                source = QBuffer()
                source.setData(QByteArray(raw))
                source.open(QIODevice.OpenModeFlag.ReadOnly)
                reader = QImageReader(source)
                if bytes(reader.format()).lower() not in (b"png", b"jpeg", b"jpg"):
                    raise ValueError()
                size = reader.size()
                if size.width() <= 0 or size.height() <= 0 or size.width()*size.height() > 16000000:
                    raise ValueError()
                reader.setAutoTransform(True)
                reader.setScaledSize(size.scaled(QSize(2048,2048), Qt.AspectRatioMode.KeepAspectRatio)
                                     if max(size.width(),size.height()) > 2048 else size)
                decoded = reader.read()
                if decoded.isNull():
                    raise ValueError()
                # Copy pixels into a fresh image rather than carrying file metadata.
                clean = QImage(decoded.size(), QImage.Format.Format_RGB888)
                clean.fill(Qt.GlobalColor.white)
                painter = QPainter(clean)
                painter.drawImage(0, 0, decoded)
                painter.end()
                encoded = QBuffer()
                encoded.open(QIODevice.OpenModeFlag.WriteOnly)
                if not clean.save(encoded, "PNG"):
                    raise ValueError()
                data = bytes(encoded.data())
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError()
                self.image_bytes = data
                self.preview.setPixmap(QPixmap.fromImage(clean).scaled(640,360,
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.upload_button.setEnabled(True)
                self.status.setText("Ready to upload. Nothing has been sent." if self.key_input.text().strip()
                    else "API key required: enter it above, then click Upload and Reconstruct. Nothing has been sent.")
            except Exception:
                self.status.setText("Cannot load image: use a valid PNG/JPEG within the displayed limits.")

        def upload(self):
            if self.image_bytes is None:
                return
            self.profile['llm']['api_key'] = self.key_input.text().strip()
            if not self.profile['llm']['api_key']:
                self.status.setText('API key required: enter it above. Nothing has been uploaded.')
                self.key_input.setFocus()
                return
            self.result_scene=None;self.review_button.hide();self.focus_choice.hide();self.focus_label.hide()
            request_profile=photo_profile(self.profile,self.quality.currentData())
            self.ticket = probe.start((request_profile, self.image_bytes))
            if self.ticket is None:
                self.status.setText("A previous request is still finishing; retry shortly.")
                return
            self.choose_button.setEnabled(False)
            self.upload_button.setEnabled(False)
            self.key_input.setEnabled(False)
            self.quality.setEnabled(False)
            self.started_at = time.monotonic()
            self.progress.show()
            self.status.setText("Reconstructing… Cancel ignores late results; it cannot cancel server work.")
            self.timer.start()

        def poll(self):
            result = probe.poll(self.ticket)
            if result is None:
                self.status.setText(f'Reconstructing… {int(time.monotonic()-self.started_at)}s elapsed. '
                    'Waiting for the service; Cancel ignores late results.')
                return
            self.timer.stop()
            self.progress.hide()
            self.key_input.setEnabled(True)
            self.quality.setEnabled(True)
            self.choose_button.setEnabled(True)
            self.upload_button.setEnabled(self.image_bytes is not None)
            if result["state"] == "success":
                from .reconstruction import parse_scene
                scene=parse_scene(result['scene_text']);objects=scene['objects']
                meshes=sum(o['geometry']['type']=='mesh' for o in objects)
                self.result_scene = result
                self.focus_choice.clear();self.focus_choice.addItem('Whole scene',None)
                for obj in objects:self.focus_choice.addItem(obj['label'],obj['id'])
                if objects:self.focus_choice.setCurrentIndex(1)
                self.focus_choice.show();self.focus_label.show()
                self.review_button.show()
                self.status.setText(f'Draft ready: {len(objects)} parts, {meshes} meshes. Open it to inspect the shape. '
                    'A valid response does not establish visual fidelity or measured dimensions.'+
                    (' This result uses only simple primitives and may not capture detailed shapes.' if not meshes else ''))
            else:
                messages = {"missing_key": "Enter an API key above and retry. Nothing has been uploaded.",
                    "incomplete": "Response was truncated. Increase the token limit in Settings and retry.",
                    "invalid_scene": "The response did not contain a valid scene. Workspace unchanged.",
                    "invalid_settings": "Correct Intelligence settings before uploading.",
                    "auth_failure": "Authentication failed. Check the key for the destination above and retry.", "unknown_model": "Model unavailable. Check Settings / Intelligence.",
                    "timeout": "Request timed out.", "rate_limited": "Service rate limit reached.",
                    "cancelled": "Cancelled; workspace unchanged."}
                self.status.setText(messages.get(result["state"], "Reconstruction failed; workspace unchanged."))

        def invalidate(self, *_):
            self.timer.stop()
            if self.ticket is not None:
                probe.cancel(self.ticket)
            self.image_bytes = None
            self.profile["llm"]["api_key"] = ""
            self.key_input.clear()

    return PhotoDialog()
