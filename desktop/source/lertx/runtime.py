"""Single-thread native scene session; methods are queued on its worker."""
from __future__ import annotations

import math
import copy
import tempfile
from pathlib import Path

from .document import SceneDocument
from .physics import PhysicsScene
from .scene import BodyMapping, NativeWorker, SimulationDisabledError, ensure_render_product
from .simulation import SimulationClock


class SceneWorker(NativeWorker):
    def __init__(self, profile):
        super().__init__(profile["rendering"]["device"])
        self.profile = profile
        self.document = None
        self.physics = None
        self.physics_error = ""
        self.clock = SimulationClock(profile["physics"]["timestep_hz"])
        self._temporary = None
        self._drafts = None
        self._snapshot_number = 0
        self.camera_path = "/LeRTXCamera"
        self.center = [0., 0., 0.]
        self.distance = 3.
        self.azimuth = -0.8
        self.elevation = 0.55
        self._cached_tick = None
        self._cached_ordinal = None
        self._settled_frames = 0
        self._runtime_configuration = None
        self._hardware_roles = set()

    def _initialize(self):
        # NativeWorker starts the command owner, but this session creates RTX
        # only in rebuild(), once its first document/runtime snapshot is ready.
        # Creating an empty renderer here immediately tears it down on the first
        # open, potentially waiting on SDK initialization before any frame exists.
        pass

    def open_document(self, filename):
        candidate = SceneDocument(filename, self.profile["workspace"]["asset_search_paths"])
        previous = self.document
        old_camera = (self.center[:], self.distance)
        self.document = candidate
        try:
            self.frame_selection(None, publish=False)
        except Exception:
            self.document = previous
            self.center, self.distance = old_camera
            raise
        self.rebuild()
        return self.status()

    def import_photo_draft(self, text, image_sha256, model, focus_id=None):
        from uuid import uuid4
        from .reconstruction import build_draft_stage,parse_scene
        if focus_id is not None and focus_id not in {o["id"] for o in parse_scene(text)["objects"]}:
            raise ValueError("Photo focus must name an object in the generated draft")
        stage = build_draft_stage(text, image_sha256, model)
        if self._drafts is None:
            self._drafts = tempfile.TemporaryDirectory(prefix="lertx-photo-")
        path = Path(self._drafts.name) / (uuid4().hex + ".usda")
        if not stage.GetRootLayer().Export(str(path)):
            raise OSError("Could not create draft workspace")
        self.open_document(str(path))
        if focus_id is not None:
            self.frame_selection('/World/Objects/'+focus_id)
            self.move_camera(zoom=.6)  # Keep nearby appendages/parts in view too.
        self.document.dirty = True
        return self.status()

    def rebuild(self):
        from pxr import Gf, Usd, UsdGeom, UsdLux
        self._selected_meshes = []
        self._hardware_roles.clear()
        self._setup_roles=set()
        self._cached_tick = None
        self._cached_ordinal = None
        self._settled_frames = 0
        self.clock.pause()
        self.clock.reset()
        self.physics = None
        self.physics_error = ""
        try:
            self.physics = PhysicsScene(self.document.stage,
                device=f"cuda:{self._gpu_index}", gravity=float(self.profile["physics"]["gravity_m_s2"]))
        except SimulationDisabledError as exc:
            self.physics_error = str(exc)
        # Render a flattened runtime copy, never inject cameras or simulated poses
        # into the authored document. Flatten resolves local asset paths.
        if self._temporary is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="lertx-runtime-")
        self._snapshot_number += 1
        filename = Path(self._temporary.name) / f"scene-{self._snapshot_number}.usdc"
        self.document.stage.Flatten().Export(str(filename))
        runtime = Usd.Stage.Open(str(filename))
        while runtime.GetPrimAtPath(self.camera_path):
            self.camera_path += "_"
        camera = UsdGeom.Camera.Define(runtime, self.camera_path)
        camera.CreateFocalLengthAttr(24.)
        camera.CreateClippingRangeAttr(Gf.Vec2f(max(self.distance/10000, 0.0001), self.distance*1000))
        UsdGeom.Xformable(camera).AddTransformOp().Set(self.camera_matrix())
        if not any(p.IsA(UsdLux.DomeLight) or p.IsA(UsdLux.DistantLight) for p in runtime.Traverse()):
            UsdLux.DomeLight.Define(runtime, self.camera_path + "Light").CreateIntensityAttr(1000.)
        rendering = self.profile["rendering"]
        ensure_render_product(runtime, self.camera_path, rendering["width"], rendering["height"], rendering["quality"])
        runtime.GetRootLayer().Save()
        self.runtime_file = filename
        runtime = None
        # Release all previous renderer/stage state before opening a replacement.
        super()._cleanup()
        # Prior snapshots are owned runtime output, not user documents. Once
        # their renderer is closed they must not accumulate across reopens.
        for previous in filename.parent.glob("scene-*"):
            if previous != filename and previous.suffix in (".usda", ".usdc"):
                previous.unlink()
        super()._initialize()
        self.open_usd(str(filename))
        self._runtime_configuration = copy.deepcopy((self.profile["rendering"], self.profile["physics"]))
        return self.status()

    def status(self):
        from pxr import UsdGeom
        import importlib.metadata
        import warp as wp
        from .host import usd_distribution
        diagnostics = {name: importlib.metadata.version(name) for name in
                       ("ovrtx", "ovstage", "newton", "warp-lang", usd_distribution(), "PySide6")}
        diagnostics["gpu"] = wp.get_device(f"cuda:{self._gpu_index}").name
        diagnostics["workspace"] = str(self.document.path.parent)
        diagnostics["temporary_directory"] = tempfile.gettempdir()
        world = self.document.stage.GetPrimAtPath("/World")
        photo_draft = bool(world and world.GetAttribute("lertx:sceneSchema").Get() == "lertx.photo-scene.v1")
        return {"path": str(self.document.path), "dirty": self.document.dirty,
                "reconstruction_status": "unverified" if photo_draft else "",
                "diagnostics": diagnostics,
                "meters_per_unit": UsdGeom.GetStageMetersPerUnit(self.document.stage),
                "hierarchy": self.document.hierarchy(), "time": self.clock.sim_time,
                "playing": self.clock.playing, "physics_error": self.physics_error, "robots": self.robot_status()}

    def robot_status(self):
        if self.physics is None or not self.physics.robots:
            return {}
        return {"positions":self.physics.robot_positions(), "following":self.physics.following,
                "live_roles":sorted(self._hardware_roles),"setup_roles":sorted(getattr(self,'_setup_roles',set()))}

    def select_joint(self,role,name):
        from .robot import description,JOINT_NAMES
        if self.physics is None or role not in self.physics.robots or name not in JOINT_NAMES:
            raise ValueError('Open the robot workspace and choose a valid joint')
        link=description(role)[2][name].find('child').get('link')
        body=self.physics.robots[role]['bodies'][link]
        return self.select(self.physics.mapping.index_to_path[body])

    def command_robot(self, role, positions=None, following=None):
        if self._hardware_roles:
            raise ValueError('Disable physical live view before commanding this simulated arm')
        if self.physics is None:
            raise ValueError("No simulated robot in this scene")
        self.physics.command_robot(role,positions,following)
        return self.status()

    def pick(self, u, v):
        from .picking import pick
        return pick(self, u, v)

    def select(self, path):
        from .picking import select
        return select(self, path)

    def drag_joint(self, role, name, value, elapsed=0.):
        if self._hardware_roles:
            raise ValueError('Disable physical live view before dragging this arm')
        if self.physics is None:
            raise ValueError('No simulated robot in this scene')
        self.physics.command_robot(role, {name: value})
        if not self.clock.playing:
            # Explicit manipulation previews real constraints/contact while paused.
            # Bound every update; never reconstruct the renderer or teleport links.
            for _ in range(4):
                self.physics.step(self.clock.dt, self.profile['physics']['substeps'])
                self.clock.sim_time += self.clock.dt
            self.publish_transforms(self.physics.render_mapping, self.physics.render_matrices())
        self._cached_tick = None
        self._settled_frames = 0
        return {**self.tick(elapsed if self.clock.playing else 0.), 'joint_target': (role, name, value)}

    def hardware_pose(self, role, positions, captured_at=None):
        import time
        if captured_at is None or not 0<=time.monotonic()-captured_at<=.25:
            raise ValueError('Physical observation expired before rendering')
        if self.physics is None:
            raise ValueError('Open the robot workspace before enabling physical live view')
        self.clock.pause()
        self.physics.apply_measured_pose(role,positions)
        self._hardware_roles.add(role)
        if hasattr(self,'_setup_roles'):self._setup_roles.discard(role)
        self.publish_transforms(self.physics.render_mapping,self.physics.render_matrices())
        self._cached_tick=None;self._settled_frames=0
        return self.tick(0.)

    def setup_pose(self,role,positions,captured_at=None):
        """Explicit guide/provisional encoder preview, never a verified observation."""
        import time
        if captured_at is not None and not 0<=time.monotonic()-captured_at<=.25:
            raise ValueError('Calibration observation expired; waiting for fresh telemetry')
        if self.physics is None:raise ValueError('Open the robot workspace for calibration preview')
        self.clock.pause();self.physics.apply_measured_pose(role,positions)
        self._hardware_roles.add(role)
        if not hasattr(self,'_setup_roles'):self._setup_roles=set()
        self._setup_roles.add(role)
        self.publish_transforms(self.physics.render_mapping,self.physics.render_matrices())
        self._cached_tick=None;self._settled_frames=0
        return self.tick(0.)

    def release_hardware(self, role):
        self._hardware_roles.discard(role)
        if hasattr(self,'_setup_roles'):self._setup_roles.discard(role)
        self._cached_tick=None;self._settled_frames=0
        return self.status()

    def set_playing(self, enabled):
        if enabled and self._hardware_roles:
            raise ValueError('Turn off physical live view before playing simulation')
        if enabled and (self.physics is None or self.physics_error):
            raise ValueError(self.physics_error or "No simulated scene")
        self.clock.play() if enabled else self.clock.pause()
        return self.status()

    def configure(self, profile, config_path):
        """Apply and persist on the native owner, restoring prior state on failure."""
        from .config import save_profile, validate_profile
        candidate = copy.deepcopy(profile)
        if not validate_profile(candidate)["valid"]:
            raise ValueError("Invalid application settings")
        if self.document is None:
            raise ValueError("Open a ready workspace before applying settings")
        previous = self.profile
        native_change = any(candidate[key] != previous[key] for key in ("rendering", "physics"))
        self.profile = candidate
        try:
            if native_change:
                self._gpu_index = candidate["rendering"]["device"]
                self.clock.set_timestep_hz(candidate["physics"]["timestep_hz"])
            status = self.rebuild() if native_change else self.status()
            save_profile(candidate, config_path)
        except Exception:
            self.profile = previous
            if native_change:
                self._gpu_index = previous["rendering"]["device"]
                self.clock.set_timestep_hz(previous["physics"]["timestep_hz"])
                try:
                    self.rebuild()
                except Exception:
                    raise RuntimeError("Settings were not saved; native restoration failed. Reopen the application.") from None
            raise ValueError("Settings were not saved; previous configuration restored.") from None
        return status

    def tick(self, elapsed):
        # Only bounded catch-up is admitted; excess wall time is dropped.
        if self.physics is not None:
            steps = self.clock.advance(min(max(elapsed, 0), 0.1))
            for _ in range(steps):
                self.physics.step(self.clock.dt, self.profile["physics"]["substeps"])
            if steps:
                self.publish_transforms(self.physics.render_mapping, self.physics.render_matrices())
        if self._cached_ordinal != self._ordinal:
            self._settled_frames = 0
        if not self.clock.playing and self._cached_tick is not None and self._settled_frames >= 4:
            return {**self._cached_tick, "unchanged": True, "playing": False}
        frame = self.render("/Render/Product", max(0., elapsed))
        result = {"frame": frame, "time": self.clock.sim_time, "playing": self.clock.playing, "robots":self.robot_status()}
        self._cached_tick = result
        self._cached_ordinal = self._ordinal
        self._settled_frames += 1
        return result

    def reset(self):
        if self._hardware_roles:
            raise ValueError('Turn off physical live view before resetting simulation')
        if self._runtime_configuration != (self.profile["rendering"], self.profile["physics"]):
            return self.rebuild()
        # Reset changes simulation state, not the scene or renderer settings.
        # Recreating RTX here adds seconds of latency and retains SDK caches.
        self.clock.pause()
        self.clock.reset()
        self.physics = None
        self.physics_error = ""
        try:
            self.physics = PhysicsScene(self.document.stage,
                device=f"cuda:{self._gpu_index}", gravity=float(self.profile["physics"]["gravity_m_s2"]))
        except SimulationDisabledError as exc:
            self.physics_error = str(exc)
        if self.physics is not None:
            self.publish_transforms(self.physics.render_mapping, self.physics.render_matrices())
        self._cached_tick = None
        self._cached_ordinal = None
        self._settled_frames = 0
        return self.status()

    def edit(self, path, translation, rotation, scale):
        self.document.edit_transform(path, translation, rotation, scale)
        return self.rebuild()

    def save(self, destination=None):
        self.document.save(destination)
        return self.status()

    def inspect(self, path):
        return self.document.transform(path)

    def begin_object_drag(self, path):
        """Current transform plus the camera basis needed to drag it in screen space."""
        from pxr import Gf
        transform = self.document.transform(path)
        matrix = self.camera_matrix()
        right = matrix.TransformDir(Gf.Vec3d(1., 0., 0.))
        up = matrix.TransformDir(Gf.Vec3d(0., 1., 0.))
        return {**transform,
                "camera_right": [float(right[0]), float(right[1]), float(right[2])],
                "camera_up": [float(up[0]), float(up[1]), float(up[2])],
                "distance": self.distance}

    def drag_object(self, path, translation, rotation, scale, elapsed=0.):
        """Cheap live preview: publish a new pose without the full edit+rebuild cost."""
        from pxr import Gf
        t = Gf.Transform()
        t.SetTranslation(Gf.Vec3d(*translation))
        r = Gf.Rotation(Gf.Vec3d(1., 0., 0.), rotation[0])
        r *= Gf.Rotation(Gf.Vec3d(0., 1., 0.), rotation[1])
        r *= Gf.Rotation(Gf.Vec3d(0., 0., 1.), rotation[2])
        t.SetRotation(r)
        t.SetScale(Gf.Vec3d(*scale))
        self.publish_transforms(BodyMapping({0: path}), [t.GetMatrix()])
        self._cached_tick = None
        self._settled_frames = 0
        return {**self.tick(elapsed if self.clock.playing else 0.), "object_target": (path, translation)}

    def camera_matrix(self):
        from pxr import Gf, UsdGeom
        axis = str(UsdGeom.GetStageUpAxis(self.document.stage))
        up = Gf.Vec3d(0, 1, 0) if axis == "Y" else Gf.Vec3d(0, 0, 1)
        horizontal = self.distance * math.cos(self.elevation)
        v = [horizontal*math.cos(self.azimuth), horizontal*math.sin(self.azimuth),
             self.distance*math.sin(self.elevation)]
        if axis == "Y":
            v = [v[0], v[2], v[1]]
        center = Gf.Vec3d(*self.center)
        return Gf.Matrix4d().SetLookAt(center + Gf.Vec3d(*v), center, up).GetInverse()

    def move_camera(self, orbit=(0, 0), pan=(0, 0), zoom=0):
        from pxr import Gf
        self.azimuth += orbit[0]
        self.elevation = max(-1.45, min(1.45, self.elevation + orbit[1]))
        matrix = self.camera_matrix()
        shift = matrix.TransformDir(Gf.Vec3d(pan[0], pan[1], 0)) * self.distance
        self.center = list(Gf.Vec3d(*self.center) + shift)
        self.distance = max(0.001, min(1e8, self.distance * math.exp(max(-2, min(2, zoom)))))
        mapping = BodyMapping({0: self.camera_path})
        self.publish_transforms(mapping, [self.camera_matrix()])

    def frame_selection(self, path=None, publish=True):
        from pxr import Usd, UsdGeom
        prim = self.document.stage.GetPrimAtPath(path) if path else self.document.stage.GetPseudoRoot()
        if not prim:
            raise ValueError("Select an existing prim")
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if path is None:
            from pxr import Gf
            robots=[p for p in self.document.stage.Traverse() if p.GetAttribute('lertx:robotModel').Get()=='so101.v1']
            if robots:
                box=Gf.Range3d()
                for robot in robots:box.UnionWith(cache.ComputeWorldBound(robot).ComputeAlignedRange())
        if box.IsEmpty():
            raise ValueError("Selected prim has no visible bounds")
        self.center = list(box.GetMidpoint())
        self.distance = max(box.GetSize().GetLength()*1.6, 0.01)
        if publish:
            self.move_camera()

    def _cleanup(self):
        try:
            super()._cleanup()
        finally:
            self._cached_tick = None
            self.physics = None
            self.document = None
            if self._temporary is not None:
                self._temporary.cleanup()
                self._temporary = None
            if self._drafts is not None:
                self._drafts.cleanup()
                self._drafts = None
