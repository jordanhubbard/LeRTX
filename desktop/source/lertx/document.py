"""Worker-owned authored USD state, separate from transient renderer poses."""
from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile


class SceneDocument:
    def __init__(self, filename, asset_search_paths=()):
        from pxr import Sdf, Tf, Usd, UsdUtils
        from .assets import preflight_layers, require_local_path

        require_local_path(str(filename))
        for value in asset_search_paths:
            require_local_path(value)
        self.path = Path(filename).resolve(strict=True)
        search_paths = [Path(p).expanduser() for p in asset_search_paths]
        search_paths = [(self.path.parent/p).resolve() if not p.is_absolute() else p.resolve()
                        for p in search_paths]
        preflight_layers(self.path, search_paths)
        # Never edit USD's process-global file layer: discard/reopen and a second
        # document must see on-disk state, not another document's unsaved edits.
        try:
            layer = Sdf.Layer.OpenAsAnonymous(str(self.path))
        except Tf.ErrorException as exc:
            raise ValueError("Could not parse USD file") from exc
        if layer is None:
            raise ValueError("Could not read USD layer")
        def anchor(asset):
            if not asset:
                return asset
            if "://" in asset:
                raise ValueError("Remote asset resolution is not enabled")
            source = (self.path.parent / asset).resolve()
            if not Path(asset).is_absolute() and not source.exists():
                for directory in search_paths:
                    candidate = (directory / asset).resolve()
                    if candidate.exists():
                        return str(candidate)
            return str(source)
        UsdUtils.ModifyAssetPaths(layer, anchor)
        try:
            self.stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadNone)
        except Tf.ErrorException as exc:
            raise ValueError("Could not compose USD scene") from exc
        if self.stage is None:
            raise ValueError("Could not open USD scene")
        self.dirty = False

    def hierarchy(self):
        return [{"path": str(p.GetPath()), "type": p.GetTypeName()}
                for p in self.stage.Traverse()]

    def transform(self, path):
        from pxr import Gf, UsdGeom

        prim = self.stage.GetPrimAtPath(path)
        if not prim or not prim.IsA(UsdGeom.Xformable):
            raise ValueError(f"{path}: prim does not support transforms")
        from .robot import robot_ancestor
        if robot_ancestor(prim):
            raise ValueError("Use the robot joint controls; articulated links cannot be transformed independently")
        xf = UsdGeom.Xformable(prim)
        if xf.TransformMightBeTimeVarying():
            raise ValueError(f"{path}: animated transforms cannot be edited")
        matrix = xf.GetLocalTransformation()
        rows = [Gf.Vec3d(*[matrix[i][j] for j in range(3)]) for i in range(3)]
        lengths = [row.GetLength() for row in rows]
        if any(s <= 1e-12 or not math.isfinite(s) for s in lengths) or matrix.GetDeterminant() <= 0:
            raise ValueError(f"{path}: singular or reflected transforms cannot be edited")
        if any(abs(Gf.Dot(rows[i], rows[j])/(lengths[i]*lengths[j])) > 1e-6
               for i in range(3) for j in range(i)):
            raise ValueError(f"{path}: sheared transforms cannot be edited")
        t = Gf.Transform(matrix)
        rotation = list(t.GetRotation().Decompose(Gf.Vec3d(0, 0, 1),
                                                Gf.Vec3d(0, 1, 0), Gf.Vec3d(1, 0, 0)))[::-1]
        return {"translation": list(t.GetTranslation()), "rotation": list(rotation),
                "scale": list(t.GetScale())}

    def edit_transform(self, path, translation, rotation, scale):
        from pxr import Gf, UsdGeom

        self.transform(path)  # Validate before mutation.
        values = (translation, rotation, scale)
        if any(len(v) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float))
                                  or not math.isfinite(x) for x in v) for v in values):
            raise ValueError("Transforms require three finite numeric components")
        if any(x <= 0 for x in scale):
            raise ValueError("Scale must be positive")
        prim = self.stage.GetPrimAtPath(path)
        xf = UsdGeom.Xformable(prim)
        reset = xf.GetResetXformStack()
        # A single matrix avoids duplicate named ops and preserves reset semantics.
        t = Gf.Transform()
        t.SetTranslation(Gf.Vec3d(*translation))
        r = Gf.Rotation(Gf.Vec3d(1, 0, 0), rotation[0])
        r *= Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation[1])
        r *= Gf.Rotation(Gf.Vec3d(0, 0, 1), rotation[2])
        t.SetRotation(r)
        t.SetScale(Gf.Vec3d(*scale))
        xf.MakeMatrixXform().Set(t.GetMatrix())
        xf.SetResetXformStack(reset)
        self.dirty = True

    def save(self, destination=None):
        """Atomically export authored root only; failed saves retain dirty state."""
        target = Path(destination).resolve() if destination else self.path
        if target.suffix.lower() not in (".usd", ".usda", ".usdc"):
            raise ValueError("Choose a .usd, .usda or .usdc filename")
        # External paths were anchored when opening the private authored layer.
        layer = self.stage.GetRootLayer()
        fd, temporary = tempfile.mkstemp(prefix=".lertx-save-", suffix=target.suffix,
                                          dir=str(target.parent))
        os.close(fd)
        try:
            if not layer.Export(temporary):
                raise OSError("USD export failed")
            # Windows FlushFileBuffers requires a writable descriptor.
            with open(temporary, "r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.path = target
        self.dirty = False
        return str(target)
