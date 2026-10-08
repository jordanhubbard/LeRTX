# Retained LeRTX application

SO-101 USB reads, explicitly armed manual writes and measured virtual bindings
are described in the [hardware guide](../docs/user/hardware.md). Emulated-bus and
earlier native viewport checks are recorded; physical-arm qualification is still pending.

## Qualification of the local follow-on work

The September 27 native reports describe earlier source snapshots. Subsequent
changes to dragging, the twelve-joint panel, poses and setup UI have separate
October Linux native evidence in
[`sdk-refresh-review.json`](../verification/sdk-refresh-review.json). The current
candidate uses OVRTX 0.5.1.385782, OVStage 0.2.1.385922, Newton 1.6.1 and Warp
1.18.0. Windows runtime/installer checks and framework admission remain open;
Linux offscreen Qt checks do not establish desktop compositor integration.
The checkout reconciliation and remaining gates are tracked in
[APP-001](../docs/roadmap/active-work.md#checkout-reconciliation--app-001-config-001-twin-001-and-robot-001).

`packaging/windows/` is an installer candidate requiring a current install,
launch, upgrade and uninstall qualification. `packaging/macos/` is deferred
launcher scaffolding: macOS is not a supported rendering target and setup fails
its platform preflight. Building a `.app` or `.dmg` does not produce a working
macOS LeRTX application. Neither packaging directory is a release artifact.

## Development setup and launch

Use Windows 11 x86-64 or Linux x86-64/ARM64 with an NVIDIA RTX GPU and
working NVIDIA driver. Linux ARM64 needs glibc 2.39 or newer for Qt (Ubuntu
24.04 or newer qualifies). Install Python 3.11 or `uv`, then from the repository:

```sh
python desktop/manage.py setup
python desktop/manage.py doctor
python desktop/manage.py install
python desktop/manage.py run
```

Use `python3` if that is your system's Python command. Setup selects Python
3.11 through `uv` when available; it keeps the runtime in `.venv` and downloads
the large native SDK wheels from PyPI/NVIDIA. It does not install GPU drivers.
Setup then renders a real test frame and prepares native caches, with a five-minute
deadline. First-install shader compilation can take several minutes. A failed
warmup is a setup failure; check available memory and the NVIDIA driver, then
use `python desktop/manage.py warmup` to retry after addressing the cause.
Linux ARM64 uses NVIDIA `usd-exchange` for `pxr`; other targets use `usd-core`.
Do not install both USD distributions in the same environment.

Open a document with `python desktop/manage.py run --scene workspace.usda`.
Run all tests with `python desktop/manage.py test` in a graphical session.
On a headless Linux worker use `xvfb-run -a python desktop/manage.py test`, or
`QT_QPA_PLATFORM=offscreen python desktop/manage.py test` for offscreen Qt
checks. Offscreen Qt still exercises the real NVIDIA renderer, but does not
prove desktop compositor integration. Test the visible window separately.
From a repository checkout, run contained Linux qualification with the application interpreter and
`verification/qualify_native.py --output _build/native-qualification-<new-name>`.
It initializes Qt before the SDK and runs native modules in separate guarded
processes, preserving test logs and resource reports. It may reuse shader caches.

`install` adds LeRTX to the desktop application menu (Windows: Start Menu).
`uninstall` removes the unchanged launcher created by this checkout and keeps
your scenes, settings and `.venv`. To upgrade a checkout, close LeRTX, update
the files, and run `setup` again. For a relocated checkout, uninstall its old
launcher first, then install from the new location.

### Windows installer

For end users who don't want to open a terminal: `desktop/packaging/windows/LeRTX.iss`
is an [Inno Setup](https://jrsoftware.org/isinfo.php) script that builds a normal
double-click `LeRTX-Setup-<version>.exe`. Build it on Windows with Inno Setup 6
or newer installed:

```powershell
"C:\Program Files\Inno Setup 6\ISCC.exe" desktop\packaging\windows\LeRTX.iss
```

Produces `dist\LeRTX-Setup-<version>.exe`. Running that installer copies the
application into `%LOCALAPPDATA%\Programs\LeRTX` (no admin rights needed),
installs a real Python 3.11 if one isn't already on PATH (the Microsoft Store's
`python.exe`/`py` stubs don't count and are detected/skipped), runs the same
`manage.py setup` flow as the manual path above, and creates a Start Menu
shortcut via the installer's own icon management. Uninstalling from "Apps &
features" removes the application directory and shortcut cleanly; your
settings and saved poses (outside the install directory) are preserved.
This still needs network access on first run to download the pinned NVIDIA
SDK wheels — it is not a fully offline single-file installer, because those
wheels are multi-gigabyte, GPU-specific native binaries unsuited to freezing
into one executable.

`python desktop/manage.py package` creates `dist/LeRTX-prototype.zip` and a
SHA-256 checksum. Extract the ZIP, enter `LeRTX`, and use the same setup commands.
This source/setup bundle downloads pinned SDKs during setup and contains no
credentials, native SDK binaries or private worker configuration. It is a
development prototype bundle, not a formally admitted release.

Installation preflight and platform eligibility are not application acceptance;
the current cross-platform qualification remains tracked in PORT-001.

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
USD editing/saving, and settings. Current 160-test suites pass on Windows 11,
Linux x86-64, Linux ARM64 and Omarchy, including real Qt launches, photo failure
preservation and simulated telemetry.
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
