"""Metal renderer exposing the OVRTX call sequence used by NativeWorker."""
from __future__ import annotations

import ctypes
from types import SimpleNamespace

import numpy as np

OVRTX_RENDER_VAR_PICK_HIT = "/Render/Vars/PickHit"
OVRTX_PICK_HIT_MAGIC = 0x4D45544C
OVRTX_PICK_HIT_VERSION = 1

_SHADER = """
#include <metal_stdlib>
using namespace metal;

struct VertexIn {
    float3 position [[attribute(0)]];
    float3 normal   [[attribute(1)]];
};
struct VertexOut {
    float4 position [[position]];
    float3 worldNormal;
};
struct Uniforms {
    float4x4 mvp;
    float4x4 model;
    float4 lightDir;
    float4 tint;
    float4 baseColor;
};

vertex VertexOut vertex_main(VertexIn in [[stage_in]], constant Uniforms& u [[buffer(1)]]) {
    VertexOut out;
    out.position = u.mvp * float4(in.position, 1.0);
    out.worldNormal = (u.model * float4(in.normal, 0.0)).xyz;
    return out;
}

fragment float4 fragment_main(VertexOut in [[stage_in]], constant Uniforms& u [[buffer(1)]]) {
    float3 n = normalize(in.worldNormal);
    float ndl = saturate(dot(n, normalize(u.lightDir.xyz)));
    float3 color = mix(u.baseColor.xyz, mix(u.baseColor.xyz, u.tint.xyz, 0.65), u.tint.w);
    float3 lit = color * (0.18 + 0.82 * ndl);
    return float4(lit, 1.0);
}
"""


class Device:
    CPU = "cpu"


class RendererConfig(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)


class SelectionGroupStyle:
    def __init__(self, outline_color=(1.0, 0.65, 0.1, 1.0), fill_color=(0.0, 0.0, 0.0, 0.0)):
        self.outline_color = outline_color
        self.fill_color = fill_color


class _Mapped:
    def __init__(self, array, params=None):
        self._array = np.ascontiguousarray(array)
        self.params = params or {}

    def __dlpack__(self, *args, **kwargs):
        return self._array.__dlpack__(*args, **kwargs)

    def __getitem__(self, key):
        if key in self.params:
            return self.params[key]
        return _Mapped(self._array)

    def unmap(self):
        return None

    def map(self, device=None):
        del device
        return self


def device_name() -> str:
    device = _metal_device()
    return str(device.name()) if device is not None else "Apple Metal"


def _metal_device():
    import Metal
    device = Metal.MTLCreateSystemDefaultDevice()
    if device is None:
        raise RuntimeError("No Metal GPU is available on this Mac.")
    return device


UNIFORM_STRIDE = 256


def _fill_buffer(buf, data: bytes, offset: int = 0):
    dest = buf.contents()
    end = offset + len(data)
    try:
        memoryview(dest)[offset:end] = data
        return
    except (TypeError, ValueError):
        pass
    try:
        dest.as_buffer(end)[offset:end] = data
        return
    except AttributeError:
        pass
    ctypes.memmove(int(dest) + offset, data, len(data))


def _gf_to_numpy(matrix):
    return np.array([[matrix[i][j] for j in range(4)] for i in range(4)], dtype=np.float64)


def _numpy_to_gf(array):
    from pxr import Gf
    matrix = Gf.Matrix4d()
    data = np.asarray(array, dtype=np.float64).reshape(4, 4)
    for i in range(4):
        matrix.SetRow(i, Gf.Vec4d(*data[i]))
    return matrix


def _local_matrix(prim, overrides):
    from pxr import Gf, UsdGeom
    path = str(prim.GetPath())
    if path in overrides:
        return _numpy_to_gf(overrides[path])
    if prim.IsA(UsdGeom.Xformable):
        return UsdGeom.Xformable(prim).GetLocalTransformation()
    return Gf.Matrix4d(1)


def _world_matrix(prim, overrides, cache=None):
    path = str(prim.GetPath())
    if cache is not None and path in cache:
        return cache[path]
    local = _local_matrix(prim, overrides)
    parent = prim.GetParent()
    if parent and not parent.IsPseudoRoot():
        matrix = local * _world_matrix(parent, overrides, cache)
    else:
        matrix = local
    if cache is not None:
        cache[path] = matrix
    return matrix


def _local_numpy(prim, overrides):
    path = str(prim.GetPath())
    if path in overrides:
        return np.asarray(overrides[path], dtype=np.float64).reshape(4, 4)
    from pxr import UsdGeom
    if prim.IsA(UsdGeom.Xformable):
        return _gf_to_numpy(UsdGeom.Xformable(prim).GetLocalTransformation())
    return np.eye(4, dtype=np.float64)


def _prim_color(prim):
    from pxr import UsdGeom, UsdShade
    gprim = UsdGeom.Gprim(prim)
    colors = gprim.GetDisplayColorAttr().Get()
    if colors:
        sample = colors[0]
        return (float(sample[0]), float(sample[1]), float(sample[2]))
    binding = UsdShade.MaterialBindingAPI(prim)
    relation = binding.GetDirectBindingRel()
    targets = relation.GetTargets() if relation else []
    if targets:
        material = UsdShade.Material(prim.GetStage().GetPrimAtPath(targets[0]))
        for child in material.GetPrim().GetChildren():
            shader = UsdShade.Shader(child)
            if shader.GetIdAttr().Get() == "UsdPreviewSurface":
                diffuse = shader.GetInput("diffuseColor")
                value = diffuse.Get() if diffuse else None
                if value is not None:
                    return (float(value[0]), float(value[1]), float(value[2]))
    return (0.62, 0.64, 0.68)


def _cube_triangles(size):
    h = float(size) * 0.5
    faces = (
        ((-h, -h, -h), (h, -h, -h), (h, h, -h), (-h, h, -h), (0, 0, -1)),
        ((-h, -h, h), (-h, h, h), (h, h, h), (h, -h, h), (0, 0, 1)),
        ((-h, -h, -h), (-h, -h, h), (h, -h, h), (h, -h, -h), (0, -1, 0)),
        ((-h, h, -h), (h, h, -h), (h, h, h), (-h, h, h), (0, 1, 0)),
        ((-h, -h, -h), (-h, h, -h), (-h, h, h), (-h, -h, h), (-1, 0, 0)),
        ((h, -h, -h), (h, -h, h), (h, h, h), (h, h, -h), (1, 0, 0)),
    )
    vertices = []
    for p0, p1, p2, p3, normal in faces:
        for a, b, c in ((p0, p1, p2), (p0, p2, p3)):
            for point in (a, b, c):
                vertices.extend((*point, *normal))
    return np.asarray(vertices, dtype=np.float32).reshape(-1, 6)


def _sphere_triangles(radius, slices=16, stacks=12):
    vertices = []
    for i in range(stacks):
        v0 = i / stacks
        v1 = (i + 1) / stacks
        phi0 = np.pi * (v0 - 0.5)
        phi1 = np.pi * (v1 - 0.5)
        y0, y1 = np.sin(phi0), np.sin(phi1)
        r0, r1 = np.cos(phi0), np.cos(phi1)
        for j in range(slices):
            u0 = j / slices
            u1 = (j + 1) / slices
            a0, a1 = 2 * np.pi * u0, 2 * np.pi * u1
            p00 = (r0 * np.cos(a0), y0, r0 * np.sin(a0))
            p10 = (r0 * np.cos(a1), y0, r0 * np.sin(a1))
            p01 = (r1 * np.cos(a0), y1, r1 * np.sin(a0))
            p11 = (r1 * np.cos(a1), y1, r1 * np.sin(a1))
            for a, b, c in ((p00, p10, p11), (p00, p11, p01)):
                for point in (a, b, c):
                    normal = np.asarray(point, dtype=np.float32)
                    normal /= max(np.linalg.norm(normal), 1e-8)
                    vertices.extend((*(np.asarray(point) * radius), *normal))
    return np.asarray(vertices, dtype=np.float32).reshape(-1, 6)


def _fan_triangles(counts, indices):
    tri_count = int(np.maximum(np.asarray(counts, dtype=np.int64) - 2, 0).sum())
    if tri_count <= 0:
        return None
    out = np.empty((tri_count, 3), dtype=np.int32)
    cursor = 0
    triangle = 0
    for count in counts:
        count = int(count)
        if count >= 3:
            origin = int(indices[cursor])
            for offset in range(1, count - 1):
                out[triangle, 0] = origin
                out[triangle, 1] = int(indices[cursor + offset])
                out[triangle, 2] = int(indices[cursor + offset + 1])
                triangle += 1
        cursor += count
    return out[:triangle]


def _triangle_mesh(points, counts, indices):
    points = np.ascontiguousarray(points, dtype=np.float32).reshape(-1, 3)
    counts = np.asarray(counts, dtype=np.int32).reshape(-1)
    indices = np.asarray(indices, dtype=np.int32).reshape(-1)
    if points.size == 0 or counts.size == 0 or indices.size == 0:
        return None
    if np.all(counts == 3):
        tris = indices.reshape(-1, 3)
    else:
        tris = _fan_triangles(counts, indices)
        if tris is None or len(tris) == 0:
            return None
    v0, v1, v2 = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    face_n = np.cross(v1 - v0, v2 - v0)
    normals = np.zeros_like(points)
    np.add.at(normals, tris[:, 0], face_n)
    np.add.at(normals, tris[:, 1], face_n)
    np.add.at(normals, tris[:, 2], face_n)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = (normals / np.maximum(lengths, 1e-8)).astype(np.float32, copy=False)
    return points, normals, np.ascontiguousarray(tris.reshape(-1), dtype=np.uint32)


def _mesh_geometry(mesh):
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    if not points or not counts or not indices:
        return None
    return _triangle_mesh(points, counts, indices)


def _packed_geometry(packed, color):
    packed = np.ascontiguousarray(packed, dtype=np.float32)
    positions = packed[:, :3]
    return {
        "positions": positions,
        "normals": packed[:, 3:6],
        "indices": None,
        "color": color,
        "bmin": positions.min(axis=0),
        "bmax": positions.max(axis=0),
    }


def _extract_drawables(stage):
    from pxr import UsdGeom
    drawables = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim):
            continue
        imageable = UsdGeom.Imageable(prim)
        if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        color = _prim_color(prim)
        item = None
        if prim.IsA(UsdGeom.Mesh):
            geometry = _mesh_geometry(UsdGeom.Mesh(prim))
            if geometry is not None:
                positions, normals, indices = geometry
                item = {
                    "positions": positions,
                    "normals": normals,
                    "indices": indices,
                    "color": color,
                    "bmin": positions.min(axis=0),
                    "bmax": positions.max(axis=0),
                }
        elif prim.IsA(UsdGeom.Cube):
            size = UsdGeom.Cube(prim).GetSizeAttr().Get() or 1.0
            item = _packed_geometry(_cube_triangles(size), color)
        elif prim.IsA(UsdGeom.Sphere):
            radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get() or 1.0
            item = _packed_geometry(_sphere_triangles(radius), color)
        if item is None:
            continue
        item["path"] = str(prim.GetPath())
        item["prim"] = prim
        drawables.append(item)
    return drawables


def _capture_xform_graph(drawables, overrides):
    nodes = {}
    for item in drawables:
        prim = item.get("prim")
        if prim is None:
            continue
        node = prim
        while node and not node.IsPseudoRoot():
            path = str(node.GetPath())
            if path not in nodes:
                parent = node.GetParent()
                parent_path = None
                if parent and not parent.IsPseudoRoot():
                    parent_path = str(parent.GetPath())
                nodes[path] = {
                    "parent": parent_path,
                    "local": _local_numpy(node, {}),
                }
            node = node.GetParent()
        item["xform_path"] = str(prim.GetPath())
    del overrides
    return nodes


def _worlds_from_graph(nodes, overrides):
    worlds = {}

    def world_of(path):
        cached = worlds.get(path)
        if cached is not None:
            return cached
        node = nodes[path]
        local = overrides[path] if path in overrides else node["local"]
        parent = node["parent"]
        matrix = np.asarray(local, dtype=np.float64).reshape(4, 4)
        if parent is not None:
            matrix = matrix @ world_of(parent)
        worlds[path] = matrix
        return matrix

    for path in nodes:
        world_of(path)
    return worlds


def _camera_matrices(stage, product_path, overrides, width, height):
    from pxr import Usd, UsdGeom, UsdRender
    product = UsdRender.Product(stage.GetPrimAtPath(product_path))
    targets = product.GetCameraRel().GetTargets() if product else []
    camera_path = str(targets[0]) if targets else "/World/Camera"
    prim = stage.GetPrimAtPath(camera_path)
    camera = UsdGeom.Camera(prim)
    gf_camera = camera.GetCamera(Usd.TimeCode.Default())
    world = _world_matrix(prim, overrides)
    gf_camera.transform = world
    aspect = max(width, 1) / float(max(height, 1))
    if gf_camera.horizontalAperture:
        gf_camera.verticalAperture = gf_camera.horizontalAperture / aspect
    frustum = gf_camera.frustum
    view = _gf_to_numpy(frustum.ComputeViewMatrix())
    proj = _gf_to_numpy(frustum.ComputeProjectionMatrix())
    return view, proj, frustum


def _ray_from_ndc(view, proj, u, v, frustum=None):
    if frustum is not None:
        from pxr import Gf
        window = frustum.GetWindow()
        minimum, maximum = window.GetMin(), window.GetMax()
        x = minimum[0] + float(u) * (maximum[0] - minimum[0])
        y = maximum[1] - float(v) * (maximum[1] - minimum[1])
        ray = frustum.ComputePickRay(Gf.Vec2d(x, y))
        direction = np.array(ray.direction, dtype=np.float64)
        norm = np.linalg.norm(direction)
        if norm < 1e-12:
            direction = np.array((0.0, 0.0, -1.0))
        else:
            direction = direction / norm
        return np.array(ray.startPoint, dtype=np.float64), direction
    clip = np.array((2.0 * u - 1.0, 1.0 - 2.0 * v, -1.0, 1.0), dtype=np.float64)
    world = clip @ np.linalg.inv(view @ proj)
    world = world / world[3]
    origin = np.linalg.inv(view)[3, :3]
    direction = world[:3] - origin
    norm = np.linalg.norm(direction)
    if norm < 1e-12:
        direction = np.array((0.0, 0.0, -1.0))
    else:
        direction = direction / norm
    return origin, direction


def _ray_triangle(origin, direction, v0, v1, v2):
    hit = _ray_triangles(origin, direction, np.stack((v0, v1, v2))[None, ...])
    return None if hit is None else hit


def _ray_triangles(origin, direction, tris):
    if tris is None or len(tris) == 0:
        return None
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    edge1 = v1 - v0
    edge2 = v2 - v0
    pvec = np.cross(direction, edge2)
    det = np.einsum("ij,ij->i", edge1, pvec)
    valid = np.abs(det) >= 1e-10
    inv = np.zeros_like(det)
    inv[valid] = 1.0 / det[valid]
    tvec = origin - v0
    u = np.einsum("ij,ij->i", tvec, pvec) * inv
    valid &= (u >= 0.0) & (u <= 1.0)
    qvec = np.cross(tvec, edge1)
    v = np.einsum("ij,ij->i", np.broadcast_to(direction, qvec.shape), qvec) * inv
    valid &= (v >= 0.0) & (u + v <= 1.0)
    t = np.einsum("ij,ij->i", edge2, qvec) * inv
    valid &= t > 1e-5
    if not np.any(valid):
        return None
    return float(np.min(np.where(valid, t, np.inf)))


def _ray_aabb(origin, direction, bmin, bmax):
    inv = 1.0 / np.where(np.abs(direction) < 1e-12, 1e-12, direction)
    t0 = (bmin - origin) * inv
    t1 = (bmax - origin) * inv
    tmin = np.minimum(t0, t1)
    tmax = np.maximum(t0, t1)
    return float(tmin.max()) <= float(tmax.min())


def _world_aabb(model, bmin, bmax):
    corners = np.array((
        (bmin[0], bmin[1], bmin[2], 1.0),
        (bmax[0], bmin[1], bmin[2], 1.0),
        (bmin[0], bmax[1], bmin[2], 1.0),
        (bmax[0], bmax[1], bmin[2], 1.0),
        (bmin[0], bmin[1], bmax[2], 1.0),
        (bmax[0], bmin[1], bmax[2], 1.0),
        (bmin[0], bmax[1], bmax[2], 1.0),
        (bmax[0], bmax[1], bmax[2], 1.0),
    ), dtype=np.float64)
    world = corners @ model
    w = world[:, 3:4]
    world = world[:, :3] / np.where(np.abs(w) < 1e-12, 1.0, w)
    return world.min(axis=0), world.max(axis=0)


class Renderer:
    def __init__(self, config=None):
        import Metal
        self._config = config or {}
        self._device = _metal_device()
        self._queue = self._device.newCommandQueue()
        self._stage = None
        self._drawables = []
        self._path_ids = {}
        self._ids_to_path = {}
        self._selection = set()
        self._styles = {1: SelectionGroupStyle()}
        self._pick = None
        self._color = None
        self._color_cpu = None
        self._depth = None
        self._size = (0, 0)
        self._cpu_frame = None
        self._usd_id = None
        self._xform_nodes = {}
        self._uniform_pool = None
        self._uniform_cpu = None
        self._gpu_allocs = 0
        self._pipeline = self._build_pipeline(Metal)

    def _build_pipeline(self, Metal):
        library, error = self._device.newLibraryWithSource_options_error_(_SHADER, None, None)
        if library is None:
            raise RuntimeError(f"Metal shader compilation failed: {error}")
        descriptor = Metal.MTLRenderPipelineDescriptor.alloc().init()
        descriptor.setVertexFunction_(library.newFunctionWithName_("vertex_main"))
        descriptor.setFragmentFunction_(library.newFunctionWithName_("fragment_main"))
        descriptor.colorAttachments().objectAtIndexedSubscript_(0).setPixelFormat_(
            Metal.MTLPixelFormatRGBA8Unorm)
        descriptor.setDepthAttachmentPixelFormat_(Metal.MTLPixelFormatDepth32Float)
        vertex = Metal.MTLVertexDescriptor.alloc().init()
        for index, offset in enumerate((0, 12)):
            attr = vertex.attributes().objectAtIndexedSubscript_(index)
            attr.setFormat_(Metal.MTLVertexFormatFloat3)
            attr.setOffset_(offset)
            attr.setBufferIndex_(0)
        vertex.layouts().objectAtIndexedSubscript_(0).setStride_(24)
        descriptor.setVertexDescriptor_(vertex)
        pipeline, error = self._device.newRenderPipelineStateWithDescriptor_error_(descriptor, None)
        if pipeline is None:
            raise RuntimeError(f"Metal pipeline creation failed: {error}")
        depth = Metal.MTLDepthStencilDescriptor.alloc().init()
        depth.setDepthCompareFunction_(Metal.MTLCompareFunctionLess)
        depth.setDepthWriteEnabled_(True)
        self._depth_state = self._device.newDepthStencilStateWithDescriptor_(depth)
        return pipeline

    def attach_ovstage(self, stage):
        self._stage = stage

    def detach_ovstage(self):
        self._stage = None
        self._drawables = []
        self._usd_id = None
        self._xform_nodes = {}

    def destroy(self):
        self.detach_ovstage()
        self._color = self._color_cpu = self._depth = self._pipeline = None

    def set_selection_group_styles(self, styles):
        self._styles = dict(styles)

    def set_selection_outline_group_strings(self, paths, group):
        if int(group) == 0:
            self._selection.difference_update(paths)
        else:
            self._selection.update(paths)

    def enqueue_pick_query(self, product_path, u0, v0, u1, v1):
        self._pick = (product_path, (float(u0) + float(u1)) * 0.5, (float(v0) + float(v1)) * 0.5)

    def resolve_prim_path_id(self, identifier):
        return self._ids_to_path.get(int(identifier), "")

    def _ensure_targets(self, Metal, width, height):
        if self._color is not None and self._size == (width, height):
            return
        color = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            Metal.MTLPixelFormatRGBA8Unorm, width, height, False)
        color.setUsage_(Metal.MTLTextureUsageRenderTarget | Metal.MTLTextureUsageShaderRead)
        color.setStorageMode_(Metal.MTLStorageModePrivate)
        staging = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            Metal.MTLPixelFormatRGBA8Unorm, width, height, False)
        staging.setUsage_(Metal.MTLTextureUsageShaderRead)
        staging.setStorageMode_(Metal.MTLStorageModeShared)
        depth = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            Metal.MTLPixelFormatDepth32Float, width, height, False)
        depth.setUsage_(Metal.MTLTextureUsageRenderTarget)
        depth.setStorageMode_(Metal.MTLStorageModePrivate)
        self._color = self._device.newTextureWithDescriptor_(color)
        self._color_cpu = self._device.newTextureWithDescriptor_(staging)
        self._depth = self._device.newTextureWithDescriptor_(depth)
        self._size = (width, height)
        self._cpu_frame = np.empty((height, width, 4), dtype=np.uint8)

    def _ensure_uniform_pool(self, Metal, count):
        rows = max(int(count), 1)
        need = rows * UNIFORM_STRIDE
        if self._uniform_cpu is None or self._uniform_cpu.shape[0] < rows:
            self._uniform_cpu = np.zeros((rows, UNIFORM_STRIDE // 4), dtype=np.float32)
        current = 0 if self._uniform_pool is None else int(self._uniform_pool.length())
        if current >= need:
            return
        self._uniform_pool = self._device.newBufferWithLength_options_(
            need, Metal.MTLResourceStorageModeShared)
        self._gpu_allocs += 1

    def _upload_geometry(self, Metal):
        shared = Metal.MTLResourceStorageModeShared
        for item in self._drawables:
            packed = np.concatenate((item["positions"], item["normals"]), axis=1)
            packed = np.ascontiguousarray(packed, dtype=np.float32)
            item["count"] = int(len(packed))
            vbuf = self._device.newBufferWithLength_options_(packed.nbytes, shared)
            _fill_buffer(vbuf, packed.tobytes())
            item["vbuf"] = vbuf
            self._gpu_allocs += 1
            indices = item.get("indices")
            if indices is None:
                item["ibuf"] = None
                continue
            indices = np.ascontiguousarray(indices, dtype=np.uint32)
            item["index_count"] = int(len(indices))
            ibuf = self._device.newBufferWithLength_options_(indices.nbytes, shared)
            _fill_buffer(ibuf, indices.tobytes())
            item["ibuf"] = ibuf
            self._gpu_allocs += 1

    def _sync_drawables(self):
        import Metal
        usd = None if self._stage is None else self._stage.usd
        if usd is None:
            self._drawables = []
            self._usd_id = None
            self._xform_nodes = {}
            return
        if self._usd_id is usd:
            return
        self._drawables = _extract_drawables(usd)
        self._usd_id = usd
        self._path_ids = {item["path"]: index + 1 for index, item in enumerate(self._drawables)}
        self._ids_to_path = {index: path for path, index in self._path_ids.items()}
        overrides = {} if self._stage is None else self._stage.xforms
        self._xform_nodes = _capture_xform_graph(self._drawables, overrides)
        self._upload_geometry(Metal)

    def step(self, render_products=None, delta_time=0.0, ordinal=0):
        del delta_time, ordinal
        import Metal
        from pxr import UsdRender
        products = render_products or {}
        product_path = next(iter(products)) if products else "/Render/Product"
        usd = None if self._stage is None else self._stage.usd
        if usd is None:
            raise RuntimeError("Metal renderer has no populated runtime stage")
        self._sync_drawables()
        product = UsdRender.Product(usd.GetPrimAtPath(product_path))
        resolution = product.GetResolutionAttr().Get() if product else None
        width = int(resolution[0]) if resolution else 1280
        height = int(resolution[1]) if resolution else 720
        self._ensure_targets(Metal, width, height)
        overrides = {} if self._stage is None else self._stage.xforms
        view, proj, frustum = _camera_matrices(usd, product_path, overrides, width, height)
        pass_desc = Metal.MTLRenderPassDescriptor.renderPassDescriptor()
        color_att = pass_desc.colorAttachments().objectAtIndexedSubscript_(0)
        color_att.setTexture_(self._color)
        color_att.setLoadAction_(Metal.MTLLoadActionClear)
        color_att.setStoreAction_(Metal.MTLStoreActionStore)
        color_att.setClearColor_(Metal.MTLClearColorMake(0.12, 0.13, 0.15, 1.0))
        depth_att = pass_desc.depthAttachment()
        depth_att.setTexture_(self._depth)
        depth_att.setLoadAction_(Metal.MTLLoadActionClear)
        depth_att.setStoreAction_(Metal.MTLStoreActionDontCare)
        depth_att.setClearDepth_(1.0)
        command = self._queue.commandBuffer()
        encoder = command.renderCommandEncoderWithDescriptor_(pass_desc)
        encoder.setRenderPipelineState_(self._pipeline)
        encoder.setDepthStencilState_(self._depth_state)
        encoder.setCullMode_(Metal.MTLCullModeNone)
        light = np.array((0.35, 0.8, 0.45), dtype=np.float32)
        style = self._styles.get(1) or SelectionGroupStyle()
        tint = np.array(style.outline_color[:3], dtype=np.float32)
        view_proj = (view @ proj).astype(np.float32)
        worlds = _worlds_from_graph(self._xform_nodes, overrides)
        n = len(self._drawables)
        self._ensure_uniform_pool(Metal, n)
        cpu = self._uniform_cpu
        valid = []
        for slot, item in enumerate(self._drawables):
            if item.get("vbuf") is None:
                continue
            model64 = worlds.get(item.get("xform_path") or item["path"])
            if model64 is None:
                continue
            item["world"] = model64
            # USD/Gf is row-vector; Metal is column-vector. Store (M*V*P) in
            # column-major order so the shader's M * p matches p * M_usd.
            cpu[slot, :16] = (model64 @ view_proj).reshape(-1)
            cpu[slot, 16:32] = model64.reshape(-1)
            cpu[slot, 32:35] = light
            cpu[slot, 36:39] = tint
            cpu[slot, 39] = 1.0 if item["path"] in self._selection else 0.0
            cpu[slot, 40:43] = np.asarray(item["color"], dtype=np.float32)
            valid.append(slot)
        rows = max(n, 1)
        _fill_buffer(self._uniform_pool, cpu[:rows].tobytes())
        for slot in valid:
            item = self._drawables[slot]
            offset = slot * UNIFORM_STRIDE
            encoder.setVertexBuffer_offset_atIndex_(item["vbuf"], 0, 0)
            encoder.setVertexBuffer_offset_atIndex_(self._uniform_pool, offset, 1)
            encoder.setFragmentBuffer_offset_atIndex_(self._uniform_pool, offset, 1)
            ibuf = item.get("ibuf")
            if ibuf is not None:
                encoder.drawIndexedPrimitives_indexCount_indexType_indexBuffer_indexBufferOffset_(
                    Metal.MTLPrimitiveTypeTriangle, item["index_count"],
                    Metal.MTLIndexTypeUInt32, ibuf, 0)
            else:
                encoder.drawPrimitives_vertexStart_vertexCount_(
                    Metal.MTLPrimitiveTypeTriangle, 0, item["count"])
        encoder.endEncoding()
        blit = command.blitCommandEncoder()
        blit.copyFromTexture_toTexture_(self._color, self._color_cpu)
        blit.endEncoding()
        command.commit()
        command.waitUntilCompleted()
        region = Metal.MTLRegionMake2D(0, 0, width, height)
        raw = (ctypes.c_ubyte * self._cpu_frame.nbytes).from_buffer(self._cpu_frame)
        self._color_cpu.getBytes_bytesPerRow_fromRegion_mipmapLevel_(
            raw, width * 4, region, 0)
        color_map = _Mapped(self._cpu_frame)
        pick_ids = np.zeros((1,), dtype=np.int32)
        pick_params = {
            "magic": _Mapped(np.array([OVRTX_PICK_HIT_MAGIC], dtype=np.int32)),
            "version": _Mapped(np.array([OVRTX_PICK_HIT_VERSION], dtype=np.int32)),
            "hitCount": _Mapped(np.array([0], dtype=np.int32)),
        }
        if self._pick is not None:
            _, u, v = self._pick
            origin, direction = _ray_from_ndc(view, proj, u, v, frustum)
            best = None
            hit_path = ""
            for item in self._drawables:
                model = item.get("world")
                if model is None:
                    continue
                bmin, bmax = _world_aabb(model, item["bmin"], item["bmax"])
                if not _ray_aabb(origin, direction, bmin, bmax):
                    continue
                positions = item["positions"]
                indices = item.get("indices")
                if indices is None:
                    count = (len(positions) // 3) * 3
                    if count == 0:
                        continue
                    tris_idx = np.arange(count, dtype=np.int64).reshape(-1, 3)
                else:
                    tris_idx = np.asarray(indices, dtype=np.int64).reshape(-1, 3)
                    count = len(tris_idx) * 3
                pts = positions[tris_idx.reshape(-1)]
                hom = np.empty((count, 4), dtype=np.float64)
                hom[:, :3] = pts
                hom[:, 3] = 1.0
                world = hom @ model
                w = world[:, 3:4]
                world = world[:, :3] / np.where(np.abs(w) < 1e-12, 1.0, w)
                t = _ray_triangles(origin, direction, world.reshape(-1, 3, 3))
                if t is not None and (best is None or t < best):
                    best = t
                    hit_path = item["path"]
            self._pick = None
            if hit_path:
                pick_ids = np.array([self._path_ids[hit_path]], dtype=np.int32)
                pick_params["hitCount"] = _Mapped(np.array([1], dtype=np.int32))
        pick_map = _Mapped(pick_ids, pick_params)
        frame = SimpleNamespace(render_vars={
            "/Render/Vars/LdrColor": color_map,
            OVRTX_RENDER_VAR_PICK_HIT: pick_map,
        })
        return {product_path: SimpleNamespace(frames=[frame])}
