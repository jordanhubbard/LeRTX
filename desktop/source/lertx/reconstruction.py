"""Untrusted photo-scene JSON to a local, explicitly unverified USD draft."""
from __future__ import annotations

import json
import math
import re

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
SCHEMA = "lertx.photo-scene.v1"


def _fail():
    # Do not echo model content: it may contain uploaded or provider-private data.
    raise ValueError("Invalid photo scene response; workspace unchanged")


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail()


def _number(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high:
        _fail()


def _triple(value, low, high):
    if not isinstance(value, list) or len(value) != 3:
        _fail()
    for number in value:
        _number(number, low, high)


def _text(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        _fail()
    if any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        _fail()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def parse_scene(text):
    """Validate all data before importing USD or constructing any scene state."""
    if not isinstance(text, str):
        _fail()
    try:
        if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
            _fail()
        scene = json.loads(text, object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: _fail())
    except (ValueError, RecursionError, UnicodeError):
        _fail()
    _fields(scene, ("schema", "units", "objects", "unobserved"))
    if scene["schema"] != SCHEMA or scene["units"] != "m":
        _fail()
    objects, unobserved = scene["objects"], scene["unobserved"]
    if not isinstance(objects, list) or not 1 <= len(objects) <= 256:
        _fail()
    if not isinstance(unobserved, list) or len(unobserved) > 64:
        _fail()
    for description in unobserved:
        _text(description, 512)
    identifiers = set()
    total_points = total_triangles = 0
    for obj in objects:
        _fields(obj, ("id", "label", "translation", "rotation", "color", "confidence", "geometry"))
        identifier = obj["id"]
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", identifier):
            _fail()
        if identifier in identifiers:
            _fail()
        identifiers.add(identifier)
        _text(obj["label"], 128)
        _triple(obj["translation"], -1000, 1000)
        _triple(obj["rotation"], -360, 360)
        _triple(obj["color"], 0, 1)
        _number(obj["confidence"], 0, 1)
        geometry = obj["geometry"]
        if not isinstance(geometry, dict):
            _fail()
        kind = geometry.get("type")
        if kind == "box":
            _fields(geometry, ("type", "size"))
            _triple(geometry["size"], 0.0001, 100)
        elif kind == "sphere":
            _fields(geometry, ("type", "radius"))
            _number(geometry["radius"], 0.0001, 100)
        elif kind == "mesh":
            _fields(geometry, ("type", "points", "triangles"))
            points, indices = geometry["points"], geometry["triangles"]
            if not isinstance(points, list) or not 3 <= len(points) <= 20000:
                _fail()
            if not isinstance(indices, list) or not 3 <= len(indices) <= 120000 or len(indices) % 3:
                _fail()
            total_points += len(points)
            total_triangles += len(indices) // 3
            if total_points > 100000 or total_triangles > 200000:
                _fail()
            for point in points:
                _triple(point, -100, 100)
            if any(type(i) is not int or not 0 <= i < len(points) for i in indices):
                _fail()
            for offset in range(0, len(indices), 3):
                a, b, c = (points[i] for i in indices[offset:offset+3])
                u, v = ([p-q for p, q in zip(end, a)] for end in (b, c))
                cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                if math.hypot(*cross) <= 1e-12:
                    _fail()
        else:
            _fail()
    return scene


def build_draft_stage(text, image_sha256, model):
    """Return an isolated USD stage; no files, network or existing stage mutated."""
    scene = parse_scene(text)
    if not isinstance(image_sha256, str) or not re.fullmatch("[0-9a-f]{64}", image_sha256):
        raise ValueError("A source image SHA256 is required")
    _text(model, 256)
    from pxr import Gf, Sdf, Usd, UsdGeom

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    for name, value in {"reconstructionStatus": "unverified", "dimensionSource": "estimated",
                        "sourceImageSHA256": image_sha256, "sourceModel": model,
                        "sceneSchema": SCHEMA}.items():
        world.CreateAttribute("lertx:" + name, Sdf.ValueTypeNames.String).Set(value)
    world.CreateAttribute("lertx:unobserved", Sdf.ValueTypeNames.StringArray).Set(scene["unobserved"])
    UsdGeom.Xform.Define(stage, "/World/Objects")
    for obj in scene["objects"]:
        path = "/World/Objects/" + obj["id"]
        geometry = obj["geometry"]
        kind = geometry["type"]
        if kind == "box":
            shape = UsdGeom.Cube.Define(stage, path)
            shape.CreateSizeAttr(1.0)
        elif kind == "sphere":
            shape = UsdGeom.Sphere.Define(stage, path)
            shape.CreateRadiusAttr(geometry["radius"])
        else:
            shape = UsdGeom.Mesh.Define(stage, path)
            shape.CreatePointsAttr([Gf.Vec3f(*p) for p in geometry["points"]])
            shape.CreateFaceVertexCountsAttr([3] * (len(geometry["triangles"]) // 3))
            shape.CreateFaceVertexIndicesAttr(geometry["triangles"])
            shape.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            shape.CreateDoubleSidedAttr(True)
            shape.CreateExtentAttr(UsdGeom.Mesh.ComputeExtent(shape.GetPointsAttr().Get()))
        transform = UsdGeom.Xformable(shape)
        transform.AddTranslateOp().Set(Gf.Vec3d(*obj["translation"]))
        transform.AddRotateXYZOp().Set(Gf.Vec3f(*obj["rotation"]))
        if kind == "box":
            transform.AddScaleOp().Set(Gf.Vec3f(*geometry["size"]))
        UsdGeom.Gprim(shape).CreateDisplayColorAttr([Gf.Vec3f(*obj["color"])])
        prim = shape.GetPrim()
        prim.SetDisplayName(obj["label"])
        prim.CreateAttribute("lertx:confidence", Sdf.ValueTypeNames.Double).Set(obj["confidence"])
    return stage
