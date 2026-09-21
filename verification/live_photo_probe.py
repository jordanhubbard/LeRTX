"""Explicit development-only image-capability probe; never imported by the app."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"desktop"/"source"))
from lertx.config import DEFAULT_PROFILE
from lertx.photo import request_scene
from lertx.reconstruction import parse_scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit("Refusing to overwrite probe evidence")
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["llm"].update(max_output_tokens=4096, timeout_seconds=120)
    try:
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
        if not key or "\n" in key or "\r" in key:
            raise ValueError()
        profile["llm"]["api_key"] = key
        image = Path(args.image).read_bytes()
        result = request_scene(profile, image)
        report = {"state": result["state"], "model": profile["llm"]["model"],
                  "max_output_tokens":4096, "timeout_seconds":120,
                  "input_sha256": hashlib.sha256(image).hexdigest(),
                  "scope":"synthetic workspace image; no measured reconstruction accuracy claim"}
        if result["state"] == "success":
            payload = parse_scene(result["scene_text"])
            if key in json.dumps(payload):
                raise ValueError()
            report["scene"] = payload
            report["object_count"] = len(payload["objects"])
        output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k != "scene"}))
        return 0 if result["state"] == "success" else 1
    except Exception:
        print('{"state":"probe_failed","detail":"No provider or credential details emitted"}')
        return 1
    finally:
        profile["llm"]["api_key"] = ""


if __name__ == "__main__":
    raise SystemExit(main())
