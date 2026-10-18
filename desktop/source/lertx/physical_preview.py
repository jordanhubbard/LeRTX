"""Application-owned read-only subscriptions to measured robot poses."""

import time


class PhysicalPreview:
    def __init__(self, owner):
        self.owner = owner
        self.roles = {}
        self.closed = False

    def track(self, controller):
        role = controller.role
        if role not in self.roles or self.roles[role]["access"].closed:
            self.roles[role] = dict(
                access=controller.acquire("observer"),
                enabled=True,
                pending=False,
                sequence=-1,
                status="Waiting for measured pose",
                at=0.0,
                generation=0,
                restore_checked=False,
                restore_error="",
            )
        else:
            self.roles[role]["enabled"] = True

    def enable(self, role, enabled):
        if role not in self.roles:
            return
        item = self.roles[role]
        item["enabled"] = enabled
        item["sequence"] = -1
        item["generation"] += 1
        if not enabled:
            item["status"] = "Paused"
            owner = self.owner
            if owner._ready and owner.worker:
                owner._command(
                    lambda: owner.worker.release_hardware(role), owner._apply_status
                )

    def disconnect(self, role):
        self.enable(role, False)
        item = self.roles.pop(role, None)
        if item:
            item["access"].stop(shutdown=True, force=False)

    def shutdown(self):
        self.closed = True
        for item in self.roles.values():
            item["access"].stop(shutdown=True, force=False)
        self.roles.clear()

    def poll(self):
        owner = self.owner
        if self.closed or owner._closing or owner.devices.closing:
            return
        for role, item in list(self.roles.items()):
            access = item["access"]
            snapshot = access.snapshot()
            sample = snapshot["sample"]
            if not item["enabled"]:
                continue
            if not snapshot["alive"] or snapshot["state"] not in ("read-only", "armed"):
                item["status"] = snapshot["error"] or snapshot["state"]
                continue
            if snapshot.get("control_owner") == "setup":
                item["status"] = "Managed by " + snapshot["control_owner"]
                continue
            if snapshot["stale"] or not sample:
                item["status"] = "Waiting for fresh telemetry"
                continue
            controller = access.controller
            if not controller.calibration or not controller.binding:
                if controller._writer is None and not item["restore_checked"]:
                    item["restore_checked"] = True
                    try:
                        controller.restore_preview_setup(owner.config_path)
                    except (ValueError, OSError) as exc:
                        item["restore_error"] = str(exc)
                        item["status"] = item["restore_error"]
                        continue
                item["status"] = (
                    item["restore_error"] or "Waiting for saved calibration and mapping"
                )
                continue
            if not owner._ready or not owner.worker:
                item["status"] = "Waiting for RTX workspace"
                continue
            if item["pending"] or sample["sequence"] == item["sequence"]:
                continue
            item["sequence"] = sample["sequence"]
            item["pending"] = True
            generation = item["generation"]

            def publish(access=access, role=role, item=item, generation=generation):
                try:
                    if (
                        self.closed
                        or not item["enabled"]
                        or access.closed
                        or generation != item["generation"]
                    ):
                        return {"physical_cancelled": True}
                    current = access.snapshot()
                    sample = current["sample"]
                    controller = access.controller
                    if current.get("control_owner") == "setup":
                        return {"physical_cancelled": True}
                    if (
                        current["stale"]
                        or not sample
                        or current["state"] not in ("read-only", "armed")
                    ):
                        raise ValueError("Waiting for fresh physical telemetry")
                    if sample.get("calibration_id") != controller.calibration.identity:
                        raise ValueError(
                            "Waiting for measurements verified with the current calibration"
                        )
                    values = (
                        sample.get("preview_observations") or sample["observations"]
                    )
                    mapped, warnings = controller.binding.map_preview(
                        {n + ".pos": v for n, v in values.items()},
                        device_id=access.device_id,
                        calibration_id=controller.calibration.identity,
                        captured_at=sample["timestamp"],
                        now=time.monotonic(),
                        normalize_gripper=controller.binding_kind == "wizard",
                    )
                    if sample["calibration_error"]:
                        warnings.insert(0, sample["calibration_error"])
                    positions = {
                        path.rsplit("/", 1)[-1]: v for path, v in mapped.items()
                    }
                    frame = owner.worker.hardware_pose(
                        role, positions, sample["timestamp"], display_only=True
                    )
                    return {**frame, "physical_preview_warning": "; ".join(warnings)}
                except Exception as exc:
                    return {"physical_preview_error": str(exc)}

            def displayed(frame, item=item, generation=generation):
                item["pending"] = False
                if (
                    frame.get("physical_cancelled")
                    or self.closed
                    or generation != item["generation"]
                ):
                    return
                if "physical_preview_error" in frame:
                    item["status"] = frame["physical_preview_error"]
                    return
                if not item["enabled"]:
                    return
                item["at"] = time.monotonic()
                item["status"] = "Live" + (
                    " · " + frame["physical_preview_warning"]
                    if frame["physical_preview_warning"]
                    else ""
                )
                owner._accept_frame(frame)

            try:
                owner._command(publish, displayed)
            except Exception as exc:
                item["pending"] = False
                item["status"] = str(exc)
        for role, label in getattr(owner, "physical_status_labels", {}).items():
            item = self.roles.get(role)
            detail = item["status"] if item else "not connected"
            summary = (
                "Live · check travel / mapping"
                if detail.startswith("Live ·")
                else detail
            )
            if len(summary) > 90:
                summary = "Preview needs attention"
            label.setText(role.title() + ": " + summary)
            label.setToolTip(detail)

    def snapshot(self):
        return {
            role: {
                key: item[key]
                for key in ("enabled", "pending", "sequence", "status", "at")
            }
            for role, item in self.roles.items()
        }
