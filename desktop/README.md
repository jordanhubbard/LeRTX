# Retained LeRTX application

The operator approved direct repair and retention of Litai-generated source on
2026-09-16. `source/` is editable application source under that explicit exception.
The Component specifications still define required behavior; all native and UI
acceptance requirements remain in force.

The original generation is retained in
`../verification/generated-baseline/source.tar` (including its generated SBOM).
The sibling baseline `source/` directory is convenient for review; a few empty
files and JSON/config files have normalized trailing newlines. The archive is
the byte-preserving reference. Repaired code is not represented as an untouched
generation or an accepted Standard lifecycle artifact.

The retained application now has a Qt window, RTX viewport, Newton simulation,
USD editing/saving, and settings. The 154-test snapshot passes on Linux and Windows,
including real Qt launches, photo failure preservation and simulated telemetry.
This is a development application, not a completed milestone or accepted
distribution. Physical robot integration is not implemented.
Do not use this application to actuate a physical robot.

Devices → Open telemetry mock exercises independent simulated leader/follower
streams without hardware. Adjust five joint-degree inputs and gripper percentage,
connect/disconnect either role, or freeze a stream to observe stale status. Mock
values do not alter USB assignments or represent calibration. Native robot-joint
rendering and the physical LeRobot reader are not yet connected to this panel.

Reconstruct Photo previews an explicitly selected PNG/JPEG, strips source metadata,
and uploads only after confirmation. Configure a session key in Settings / Intelligence
first. The configured output limit is respected; a truncated response asks you to
increase it rather than importing partial geometry. Drafts require Save As and retain
an unverified/estimated-dimensions warning after reopening. The importer supports
boxes, spheres and bounded triangle meshes. Live image inference succeeded with a
synthetic workspace render; this is not proof of measured real-world accuracy.

Launch from `desktop/source` with the provisioned, pinned SDK Python:

```sh
python main.py '[{"command":"launch"}]'
```

The runtime never downloads dependencies. The supplied SDK environment must contain
the exact distributions in `source/requirements.txt`, including Qt. Local worker
paths and test-environment overlays are private deployment details, not application
defaults. Portable defaults can be queried with `[{"command":"defaults"}]`.

Document tests on a provisioned SDK Python:

```sh
cd desktop/source
PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_document -v
```

Missing USD is a test failure, not a skip. This target does not claim rendering,
physics, UI, or complete application acceptance.
