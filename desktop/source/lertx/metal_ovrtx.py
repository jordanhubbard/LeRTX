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
    float3 color    [[attribute(2)]];
};
struct VertexOut {
    float4 position [[position]];
    float3 worldNormal;
    float3 color;
};
struct Uniforms {
    float4x4 mvp;
    float4x4 model;
    float3 lightDir;
};

vertex VertexOut vertex_main(VertexIn in [[stage_in]], constant Uniforms& u [[buffer(1)]]) {
    VertexOut out;
    out.position = u.mvp * float4(in.position, 1.0);
    out.worldNormal = (u.model * float4(in.normal, 0.0)).xyz;
    out.color = in.color;
    return out;
}

fragment float4 fragment_main(VertexOut in [[stage_in]], constant Uniforms& u [[buffer(1)]]) {
    float3 n = normalize(in.worldNormal);
    float ndl = saturate(dot(n, normalize(u.lightDir)));
    float3 lit = in.color * (0.18 + 0.82 * ndl);
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


def _fill_buffer(buf, data: bytes):
    dest = buf.contents()
    try:
        memoryview(dest)[:len(data)] = data
        return
    except (TypeError, ValueError):
        pass
    try:
        dest.as_buffer(len(data))[:] = data
        return
    except AttributeError:
        pass
    ctypes.memmove(int(dest), data, len(data))


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


def _world_matrix(prim, overrides):
    from pxr import Gf
    matrix = Gf.Matrix4d(1)
    node = prim
    while node and not node.IsPseudoRoot():
        matrix = matrix * _local_matrix(node, overrides)
        node = node.GetParent()
    return matrix


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


def _mesh_triangles(mesh):
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    if not points or not counts or not indices:
        return None
    points = np.asarray(points, dtype=np.float32)
    vertices = []
    cursor = 0
    for count in counts:
        face = [int(indices[cursor + i]) for i in range(int(count))]
        cursor += int(count)
        if len(face) < 3:
            continue
        origin = points[face[0]]
        for i in range(1, len(face) - 1):
            a, b, c = origin, points[face[i]], points[face[i + 1]]
            normal = np.cross(b - a, c - a)
            length = np.linalg.norm(normal)
            if length < 1e-12:
                normal = np.array((0.0, 0.0, 1.0), dtype=np.float32)
            else:
                normal = normal / length
            for point in (a, b, c):
                vertices.extend((*point, *normal))
    if not vertices:
        return None
    return np.asarray(vertices, dtype=np.float32).reshape(-1, 6)


def _extract_drawables(stage):
    from pxr import UsdGeom
    drawables = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim):
            continue
        imageable = UsdGeom.Imageable(prim)
        if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        geometry = None
        if prim.IsA(UsdGeom.Mesh):
            geometry = _mesh_triangles(UsdGeom.Mesh(prim))
        elif prim.IsA(UsdGeom.Cube):
            size = UsdGeom.Cube(prim).GetSizeAttr().Get() or 1.0
            geometry = _cube_triangles(size)
        elif prim.IsA(UsdGeom.Sphere):
            radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get() or 1.0
            geometry = _sphere_triangles(radius)
        if geometry is None:
            continue
        if geometry.shape[1] == 6:
            color = _prim_color(prim)
            geometry = np.concatenate([geometry, np.broadcast_to(color, (len(geometry), 3))], axis=1)
        drawables.append({"path": str(prim.GetPath()), "prim": prim, "local": np.ascontiguousarray(geometry, dtype=np.float32)})
    return drawables


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
    edge1 = v1 - v0
    edge2 = v2 - v0
    pvec = np.cross(direction, edge2)
    det = np.dot(edge1, pvec)
    if abs(det) < 1e-10:
        return None
    inv = 1.0 / det
    tvec = origin - v0
    u = np.dot(tvec, pvec) * inv
    if u < 0 or u > 1:
        return None
    qvec = np.cross(tvec, edge1)
    v = np.dot(direction, qvec) * inv
    if v < 0 or u + v > 1:
        return None
    t = np.dot(edge2, qvec) * inv
    return t if t > 1e-5 else None


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
        self._depth = None
        self._size = (0, 0)
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
        for index, (offset, fmt) in enumerate((
            (0, Metal.MTLVertexFormatFloat3),
            (12, Metal.MTLVertexFormatFloat3),
            (24, Metal.MTLVertexFormatFloat3),
        )):
            attr = vertex.attributes().objectAtIndexedSubscript_(index)
            attr.setFormat_(fmt)
            attr.setOffset_(offset)
            attr.setBufferIndex_(0)
        vertex.layouts().objectAtIndexedSubscript_(0).setStride_(36)
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

    def destroy(self):
        self.detach_ovstage()
        self._color = self._depth = self._pipeline = None

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
        color.setStorageMode_(Metal.MTLStorageModeShared)
        depth = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            Metal.MTLPixelFormatDepth32Float, width, height, False)
        depth.setUsage_(Metal.MTLTextureUsageRenderTarget)
        depth.setStorageMode_(Metal.MTLStorageModePrivate)
        self._color = self._device.newTextureWithDescriptor_(color)
        self._depth = self._device.newTextureWithDescriptor_(depth)
        self._size = (width, height)

    def _sync_drawables(self):
        usd = None if self._stage is None else self._stage.usd
        if usd is None:
            self._drawables = []
            return
        if getattr(self, "_usd_id", None) is usd:
            return
        self._drawables = _extract_drawables(usd)
        self._usd_id = usd
        self._path_ids = {item["path"]: index + 1 for index, item in enumerate(self._drawables)}
        self._ids_to_path = {index: path for path, index in self._path_ids.items()}

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
        light = np.array((0.35, 0.8, 0.45), dtype=np.float32)
        style = self._styles.get(1) or SelectionGroupStyle()
        shared = Metal.MTLResourceStorageModeShared
        for item in self._drawables:
            prim = usd.GetPrimAtPath(item["path"])
            if not prim:
                continue
            model = _gf_to_numpy(_world_matrix(prim, overrides)).astype(np.float32)
            # USD/Gf is row-vector; Metal is column-vector. Store (M*V*P) in
            # column-major order so the shader's M * p matches p * M_usd.
            mvp = (model @ view @ proj).astype(np.float32)
            uniforms = np.zeros(64, dtype=np.float32)
            uniforms[:16] = np.ascontiguousarray(mvp).reshape(-1)
            uniforms[16:32] = np.ascontiguousarray(model).reshape(-1)
            uniforms[32:35] = light
            ubuf = self._device.newBufferWithLength_options_(256, shared)
            _fill_buffer(ubuf, uniforms.tobytes())
            vertices = item["local"]
            if item["path"] in self._selection:
                vertices = vertices.copy()
                tint = np.array(style.outline_color[:3], dtype=np.float32)
                vertices[:, 6:9] = 0.35 * vertices[:, 6:9] + 0.65 * tint
            packed = np.ascontiguousarray(vertices, dtype=np.float32)
            vbuf = self._device.newBufferWithLength_options_(packed.nbytes, shared)
            _fill_buffer(vbuf, packed.tobytes())
            encoder.setVertexBuffer_offset_atIndex_(vbuf, 0, 0)
            encoder.setVertexBuffer_offset_atIndex_(ubuf, 0, 1)
            encoder.setFragmentBuffer_offset_atIndex_(ubuf, 0, 1)
            encoder.drawPrimitives_vertexStart_vertexCount_(
                Metal.MTLPrimitiveTypeTriangle, 0, len(packed))
        encoder.endEncoding()
        command.commit()
        command.waitUntilCompleted()
        nbytes = height * width * 4
        raw = (ctypes.c_ubyte * nbytes)()
        region = Metal.MTLRegionMake2D(0, 0, width, height)
        self._color.getBytes_bytesPerRow_fromRegion_mipmapLevel_(
            raw, width * 4, region, 0)
        pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4).copy()
        pixels = np.flipud(pixels)
        color_map = _Mapped(pixels)
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
                prim = usd.GetPrimAtPath(item["path"])
                if not prim:
                    continue
                model = _gf_to_numpy(_world_matrix(prim, overrides))
                local = item["local"].reshape(-1, 3, 9)
                for triangle in local:
                    points = []
                    for vertex in triangle:
                        hom = model.T @ np.array((vertex[0], vertex[1], vertex[2], 1.0))
                        points.append(hom[:3] / hom[3])
                    t = _ray_triangle(origin, direction, *points)
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
