import unittest
from types import SimpleNamespace
from unittest.mock import patch
from lertx.scene import NativeWorker


class WorkerTests(unittest.TestCase):
    def test_scene_worker_does_not_create_an_unused_renderer_at_thread_start(self):
        from lertx.config import DEFAULT_PROFILE
        from lertx.runtime import SceneWorker
        worker = SceneWorker(DEFAULT_PROFILE)
        with patch("lertx.host.check_native_support"), \
                patch.object(NativeWorker, "_initialize") as initialize:
            worker.start()
            try:
                worker.submit(lambda: None).result(timeout=2)
                initialize.assert_not_called()
                self.assertIsNone(worker._renderer)
                self.assertIsNone(worker._stage)
            finally:
                worker.stop()

    def test_usd_stage_bootstrap_precedes_renderer_and_attachment(self):
        events = []
        configurations = []
        class Renderer:
            def __init__(self, config):
                events.append("renderer")
                configurations.append(config)
            def attach_ovstage(self, stage):
                events.append("attach")
        def bootstrap():
            events.append("usd-stage")
            return object()
        modules = {
            "pxr": SimpleNamespace(Usd=SimpleNamespace(Stage=SimpleNamespace(CreateInMemory=bootstrap))),
            "ovrtx": SimpleNamespace(RendererConfig=lambda **kwargs: kwargs, Renderer=Renderer),
            "ovstage": SimpleNamespace(Stage=lambda name: object()),
        }
        with patch.dict("sys.modules", modules):
            NativeWorker()._initialize()
        self.assertEqual(events, ["usd-stage", "renderer", "attach"])
        self.assertEqual(configurations, [{"active_cuda_gpus": "0",
                                           "keep_system_alive": False}])

    def test_failed_usd_bootstrap_does_not_construct_renderer(self):
        from unittest.mock import Mock
        renderer = Mock()
        modules = {
            "pxr": SimpleNamespace(Usd=SimpleNamespace(Stage=SimpleNamespace(CreateInMemory=lambda: None))),
            "ovrtx": SimpleNamespace(Renderer=renderer),
        }
        with patch.dict("sys.modules", modules):
            with self.assertRaisesRegex(RuntimeError, "Could not initialize OpenUSD"):
                NativeWorker()._initialize()
        renderer.assert_not_called()

    def test_recoverable_command_failure_keeps_worker_alive(self):
        class Worker(NativeWorker):
            def _initialize(self):
                self.cleaned = False
            def _cleanup(self):
                self.cleaned = True
        worker = Worker()
        with patch("lertx.host.check_native_support"):
            worker.start()
        def fail():
            raise ValueError("Invalid transform")
        try:
            with self.assertRaisesRegex(ValueError, "Invalid transform"):
                worker.submit(fail).result(timeout=2)
            self.assertEqual(worker.submit(lambda: 42).result(timeout=2), 42)
        finally:
            worker.stop()
        self.assertTrue(worker.cleaned)
        with self.assertRaises(RuntimeError):
            worker.submit(lambda: 0).result(timeout=2)
