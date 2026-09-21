"""Local-only USD dependency preflight before stage composition."""
from __future__ import annotations

import os
from pathlib import Path
import re


def require_local_path(value):
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("Asset path must be local text")
    if value.startswith(("//", "\\\\")):
        raise ValueError("Network asset paths are not enabled")
    scheme = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value)
    drive = os.name == "nt" and re.match(r"^[a-zA-Z]:[\\/]", value)
    if scheme and not drive:
        raise ValueError("Remote or resolver-scheme assets are not enabled")


def preflight_layers(filename, search_paths=(), max_layers=512):
    """Inspect root, sublayers, references and payloads without opening a stage.

    Plain local USD layers only. Missing composition dependencies are errors;
    texture existence remains the renderer's diagnostic responsibility.
    """
    from pxr import Sdf, Tf, UsdUtils

    require_local_path(str(filename))
    for path in search_paths:
        require_local_path(str(path))
    seen = set()
    pending = [Path(filename)]
    while pending:
        path = pending.pop().resolve(strict=True)
        if path in seen:
            continue
        seen.add(path)
        if len(seen) > max_layers:
            raise ValueError("USD layer dependency limit exceeded")
        if path.suffix.lower() not in (".usd", ".usda", ".usdc"):
            raise ValueError("Packaged or custom-format USD dependencies are not supported")
        try:
            layer = Sdf.Layer.OpenAsAnonymous(str(path))
        except Tf.ErrorException as exc:
            raise ValueError("Could not parse USD file") from exc
        if layer is None:
            raise ValueError("Could not read USD dependency")
        def inspect(asset):
            require_local_path(asset)
            return asset
        UsdUtils.ModifyAssetPaths(layer, inspect)
        for asset in layer.GetExternalReferences():
            require_local_path(asset)
            if not asset:
                continue
            candidate = path.parent / asset
            if not candidate.exists() and not Path(asset).is_absolute():
                candidate = next((Path(base)/asset for base in search_paths
                                  if (Path(base)/asset).exists()), candidate)
            pending.append(candidate)
    return len(seen)
