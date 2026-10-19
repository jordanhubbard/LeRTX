# Retained LeRTX application

The dependency-refresh branch targets OVRTX 0.6.0.1791947691, OVStage 0.3.0.1791986420, Newton
1.7.0 and Warp 1.18.0. The source/setup ZIP is the release artifact. Earlier SDK
Linux qualification is recorded in `verification/upstream-release-review.json`
in the repository; older cross-platform reports apply to earlier SDK snapshots.
Windows x86-64 qualification is recorded in
`verification/windows-qualification-review.json`. Fresh ARM64 validation and
physical-arm qualification remain follow-up coverage. Native installer candidates
are not included in this release.


SO-101 USB reads, explicitly armed manual writes and measured virtual bindings
are described in the [hardware guide](../docs/user/hardware.md). Emulated-bus and
native viewport checks pass; physical-arm qualification is still pending.

## Development setup and launch

Use `make run` from the repository root with GNU Make installed. On Windows it
uses `run.ps1`; on Linux and macOS it uses `python3 desktop/manage.py run`
(select another interpreter with `make run PYTHON=python3.11`). It builds
missing or stale environments before launch. macOS installs the Darwin hash lock
(no OVRTX/OVStage) and warms up the Metal renderer.

Windows contributors can build and launch from the repository root with
`.\run.ps1` in PowerShell. `python desktop/manage.py run` also performs setup
automatically when no current successful setup receipt exists. A receipt is
written only after dependency installation, diagnostics and native warmup pass;
changed locks, bundled wheels, requirements or setup code trigger setup again.
An interrupted or failed setup is retried on the next launch. Explicit `setup`
still forces a refresh. This command launches in the invoking user's desktop
session; a coding sandbox's desktop may not be visible to the operator.

`make build` checks that same receipt and refreshes dependencies only when needed.
`make install` prepares the environment and installs the Start Menu/desktop shortcut;
repeating it accepts an unchanged shortcut owned by this checkout. Edited or foreign
shortcuts require explicit removal before replacement. Neither target requires Unix
`touch` on Windows.

Use Windows 11 x86-64 or Linux x86-64/ARM64 with an NVIDIA RTX GPU and
working NVIDIA driver, or macOS 11+ with Metal. Linux ARM64 needs glibc 2.39
or newer for Qt (Ubuntu 24.04 or newer qualifies). Install Python 3.11 or `uv`.

The pinned Warp 1.18 runtime requires NVIDIA R580 or newer for GPU physics;
choose a platform/GPU-specific driver supported by
[OVRTX](https://nvidia-omniverse.github.io/ovrtx/driver_requirements.html).
[Newton 1.7 migration notes](https://github.com/newton-physics/newton/releases/tag/v1.7.0)
describe the driver constraint. This branch does not install or change drivers.

From the repository:

```sh
python desktop/manage.py setup
python desktop/manage.py doctor
python desktop/manage.py install
python desktop/manage.py run
```

Use `python3` if that is your system's Python command. Setup selects Python
3.11 through `uv` when available; it keeps the runtime in `.venv` and downloads
the large native SDK wheels from PyPI (and NVIDIA on Linux/Windows). It does not
install GPU drivers. Darwin never downloads `ovrtx` or `ovstage`.
Setup then renders a real test frame and prepares native caches, with a fifteen-minute
process deadline, including up to fourteen minutes for the first frame. First-install
Windows shader compilation can exceed five minutes. A failed
warmup is a setup failure; check available memory and the GPU driver, then
use `python desktop/manage.py warmup` to retry after addressing the cause.
Linux ARM64 uses NVIDIA `usd-exchange` for `pxr`; other targets use `usd-core`.
Do not install both USD distributions in the same environment.

Open a document with `python desktop/manage.py run --scene workspace.usda`.
Run all tests with `python desktop/manage.py test` in a graphical session.
On a headless Linux worker use `xvfb-run -a python desktop/manage.py test`, or
`QT_QPA_PLATFORM=offscreen python desktop/manage.py test` for offscreen Qt
checks. Offscreen Qt still exercises the real NVIDIA renderer, but does not
prove desktop compositor integration. Test the visible window separately.

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

### macOS app bundle

macOS 11+ is a Metal rendering target. Setup installs `desktop/locks/darwin-arm64.txt`
or `darwin-x86_64.txt` (usd-core, Newton on CPU, Warp, Qt, PyObjC Metal) and
never installs OVRTX or OVStage. This is not an RTX/DLSS quality claim.
`desktop/packaging/macos/build.sh [version]` builds `dist/LeRTX.app` and
`dist/LeRTX-<version>.dmg`:

```sh
desktop/packaging/macos/build.sh 0.2.0
```

Double-clicking the bundle finds a real Python 3.11/3.12 (Homebrew or
python.org; the Xcode Command Line Tools' `/usr/bin/python3` doesn't count),
stages the bundled source into `~/Library/Application Support/LeRTX/checkout`
(required because Gatekeeper may run the bundle from a read-only translocated
path), and runs the same `manage.py setup`/`run` flow as the other platforms.
No Python auto-install is attempted (unlike Windows): installing Python
system-wide on macOS needs admin rights, so a missing interpreter dialog points
you to python.org or `brew install python@3.11`.

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
USD editing/saving, and settings. Baseline 160-test suites passed on Windows 11,
Linux x86-64, Linux ARM64 and Omarchy, including real Qt launches, photo failure
preservation and simulated telemetry.
This is a development application, not a completed milestone or accepted
distribution. Physical integration now includes guided SO-101 calibration, measured
RTX motion, joint recording and explicit bounded follower tracking/playback. The
operator has saved both real-arm calibrations and confirmed the interactive flow;
this does not qualify collision-aware autonomous motion. Read the
[hardware guide](../docs/user/hardware.md) before connecting arms.

Device Manager's **USB camera** tab lets you identify a camera by live preview and
confirm **Use this camera**. Its shared feed appears above the 3D view in the same
window. The camera backend supports Windows and Linux; stable identities are saved,
and Linux enumeration-only devices remain session-only. Camera preview does not
record video. **Robot session** exposes recording, replay, following, Danger and
The Signal alongside the RTX/camera views.

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

### SDK refresh qualification

Current results are in `verification/native/public-sdk-20261017/`: the rebased
source passes 346 tests on Apple M4 Pro using Metal and Newton 1.7 CPU physics.
The updated Linux SDK archives and interpreter compatibility are verified;
native Linux installation/execution awaits adequate worker disk space. Windows
and ARM64 runtime qualification remain open. The framework authority and locks
pass, but the acceptance receipt and Linux native source binding are not current.

Asset tooling selects URDF converter 0.3.4 and Newton USD schemas 0.6.0. Its
USD Exchange dependency provides Linux/Windows wheels only, so these conversion
tools cannot be installed on macOS. Bundled assets retain their original
converter provenance; this refresh does not claim newly converted assets.
