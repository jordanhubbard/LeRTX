"""Render the validated live-probe scene using the retained application worker."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--response", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--verify-edit", action="store_true")
args = parser.parse_args()
sys.path.insert(0, args.source)
from lertx.config import DEFAULT_PROFILE
from lertx.runtime import SceneWorker
from PySide6.QtGui import QImage

report = json.loads(Path(args.response).read_text())
if report["state"] != "success":
    raise SystemExit("Live inference did not succeed")
destination = Path(args.output)
destination.mkdir(exist_ok=False)
profile = copy.deepcopy(DEFAULT_PROFILE)
profile["rendering"].update(width=640, height=480)
worker = SceneWorker(profile)
worker.start()
def call(operation):
    return worker.submit(operation).result(timeout=120)
try:
    status = call(lambda: worker.import_photo_draft(json.dumps(report["scene"]), report["input_sha256"], report["model"]))
    frame = call(lambda: worker.tick(0))["frame"]
    fmt = QImage.Format.Format_RGBA8888 if frame.channels == 4 else QImage.Format.Format_RGB888
    image = QImage(frame.data, frame.width, frame.height, frame.width*frame.channels, fmt).copy()
    if not image.save(str(destination/"reconstructed.png")):
        raise RuntimeError("Frame export failed")
    call(lambda: worker.save(str(destination/"reconstructed.usda")))
    evidence = {"state":"rendered", "reconstruction_status":status["reconstruction_status"],
                "width":frame.width, "height":frame.height,
                "frame_sha256":hashlib.sha256(frame.data).hexdigest(),
                "usd_sha256":hashlib.sha256((destination/"reconstructed.usda").read_bytes()).hexdigest(),
                "physics_error":status["physics_error"],
                "scope":"live model output rendered; no measured spatial accuracy claim"}
    if args.verify_edit:
        prim_path = "/World/Objects/" + report["scene"]["objects"][0]["id"]
        original = call(lambda: worker.inspect(prim_path))
        translated = list(original["translation"])
        translated[0] += .125
        edited = call(lambda: worker.edit(prim_path, translated, original["rotation"], original["scale"]))
        assert edited["dirty"] and edited["reconstruction_status"] == "unverified"
        edited_path = destination/"edited.usda"
        saved = call(lambda: worker.save(str(edited_path)))
        assert not saved["dirty"]
        reopened = call(lambda: worker.open_document(str(edited_path)))
        actual = call(lambda: worker.inspect(prim_path))["translation"]
        assert all(abs(a-b) < 1e-8 for a,b in zip(actual, translated))
        assert reopened["reconstruction_status"] == "unverified"
        edited_frame = call(lambda: worker.tick(0))["frame"]
        assert edited_frame.data != frame.data and len(set(edited_frame.data)) > 16
        edited_image = QImage(edited_frame.data, edited_frame.width, edited_frame.height,
                             edited_frame.width*edited_frame.channels, fmt).copy()
        assert edited_image.save(str(destination/"edited.png"))
        evidence["edit_verification"] = {
            "prim":prim_path, "translation":actual, "saved_and_reopened":True,
            "unverified_warning_preserved":True,
            "usd_sha256":hashlib.sha256(edited_path.read_bytes()).hexdigest(),
            "frame_sha256":hashlib.sha256(edited_frame.data).hexdigest()}
finally:
    worker.stop()
evidence["worker_closed"] = worker._thread is None
(destination/"review.json").write_text(json.dumps(evidence, indent=2)+"\n")
print(json.dumps(evidence))
