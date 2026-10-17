"""Graphics facade and Darwin shims must not import NVIDIA packages."""
import inspect
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from lertx import graphics, host, metal_ovrtx, metal_ovstage


class GraphicsTests(unittest.TestCase):
    def test_darwin_selects_metal_and_cpu_physics_without_importing_ovrtx(self):
        sys.modules.pop("ovrtx", None)
        sys.modules.pop("ovstage", None)
        with patch.object(graphics.sys, "platform", "darwin"):
            self.assertEqual(graphics.backend(), "metal")
            self.assertEqual(graphics.physics_device(3), "cpu")
            self.assertIs(graphics.ovrtx(), metal_ovrtx)
            self.assertIs(graphics.ovstage(), metal_ovstage)
        self.assertNotIn("ovrtx", sys.modules)
        self.assertNotIn("ovstage", sys.modules)

    def test_nvidia_hosts_keep_real_sdk_imports_and_cuda_devices(self):
        fake_ovrtx = SimpleNamespace(name="ovrtx")
        fake_ovstage = SimpleNamespace(name="ovstage")
        with patch.object(graphics.sys, "platform", "linux"), \
                patch.dict(sys.modules, {"ovrtx": fake_ovrtx, "ovstage": fake_ovstage}):
            self.assertEqual(graphics.backend(), "ovrtx")
            self.assertEqual(graphics.physics_device(2), "cuda:2")
            self.assertIs(graphics.ovrtx(), fake_ovrtx)
            self.assertIs(graphics.ovstage(), fake_ovstage)

    def test_host_admits_macos_and_still_rejects_unknown_machines(self):
        for system, machine in (("darwin", "arm64"), ("darwin", "x86_64")):
            with self.subTest(system=system, machine=machine), \
                    patch.object(host.sys, "platform", system), \
                    patch.object(host.sys, "version_info", SimpleNamespace(major=3, minor=11)), \
                    patch.object(host.platform, "machine", return_value=machine):
                host.check_native_support()
                self.assertEqual(host.usd_distribution(), "usd-core")

    def test_metal_ovstage_publishes_xform_overrides(self):
        stage = metal_ovstage.Stage("shim")
        paths = metal_ovstage.PathDictionary(stage)
        matrix = np.eye(4, dtype=np.float64)
        matrix[3, :3] = (1.0, 2.0, 3.0)
        tensor = metal_ovstage.make_dltensor(
            matrix.reshape(1, 16),
            dtype=metal_ovstage.DLDataType(
                code=metal_ovstage.DLDataTypeCode.kDLFloat, bits=64, lanes=16),
            shape=[1],
        )
        with paths.create_path_list_from_strings(["/World/Obstacle"]) as path_list:
            with stage.query_from_path_list(path_list) as query:
                stage.write_attribute(
                    query, paths.intern_token("omni:xform"), ordinal=4, tensors=tensor
                ).wait()
                stage.advance_write_floor(4, metal_ovstage.Scope.ALL).wait()
        self.assertEqual(stage.ordinal, 4)
        self.assertTrue(np.allclose(stage.xforms["/World/Obstacle"][3, :3], (1.0, 2.0, 3.0)))

    def test_metal_tessellates_cube_and_sphere(self):
        cube = metal_ovrtx._cube_triangles(2.0)
        self.assertEqual(cube.shape[1], 6)
        self.assertEqual(len(cube) % 3, 0)
        self.assertGreater(len(cube), 0)
        sphere = metal_ovrtx._sphere_triangles(0.5)
        self.assertEqual(sphere.shape[1], 6)
        self.assertGreater(len(sphere), len(cube))

    def test_triangle_mesh_keeps_shared_vertices(self):
        points = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), dtype=np.float32)
        counts = np.array((3, 3), dtype=np.int32)
        indices = np.array((0, 1, 2, 0, 2, 3), dtype=np.int32)
        positions, normals, index_buffer = metal_ovrtx._triangle_mesh(points, counts, indices)
        self.assertEqual(len(positions), 4)
        self.assertEqual(len(normals), 4)
        self.assertEqual(len(index_buffer), 6)
        self.assertTrue(np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-5))

    def test_metal_step_keeps_framebuffer_origin_and_reuses_buffers(self):
        source = inspect.getsource(metal_ovrtx.Renderer.step)
        self.assertNotIn("flipud", source)
        self.assertNotIn("newBufferWithLength", source)
        self.assertNotIn("newBufferWithBytes", source)
        self.assertIn("vbuf", source)
        self.assertIn("_uniform_pool", source)
        self.assertIn("drawIndexedPrimitives", source)
        self.assertIn("tint", metal_ovrtx._SHADER)
