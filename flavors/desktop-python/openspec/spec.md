# Native Python desktop requirements

### Requirement: Native Python application and portable bootstrap

Implement `source/main.py` with callable `main(payload)` and the JSON argument
array wrapper from the selected application implementation skill. Use Python
3.11 or 3.12 for native GPU execution on Linux x86-64, Linux ARM64 and Windows
11 x86-64. Linux includes Ubuntu and Arch/Omarchy; ARM64 requires glibc 2.39
or newer for the pinned Qt wheels. The
defaults command and portable tests must also run on the macOS bootstrap Python
without importing unavailable native packages. Native commands must reject an
unsupported host or Python ABI with an actionable error before SDK initialization.

Use these exact runtime distributions and declare them honestly in requirements
and the source SBOM: `ovrtx==0.5.1.385782`, `ovstage==0.2.1.385922`,
`newton==1.6.1`, `warp-lang==1.18.0`, `usd-core==26.8`,
`PySide6==6.12.0`, `pyserial==3.5`, and the locally supplied
`lertx-robot-assets==1.0.0` resource wheel. The unchanged, vendored
`feetech-servo-sdk==1.0.0` source and license are part of the application payload,
with archive/file hashes in `lertx/vendor/feetech/provenance.json`.
On Linux ARM64 use `usd-exchange==3.0.1` instead of
`usd-core`: its wheel supplies the native `pxr` bindings and OpenUSD libraries.
Never install both USD distributions into one environment. Acquire the exact
OVRTX wheel from NVIDIA's public Python index when PyPI only provides a stub.
Use `numpy==2.4.6` on Python 3.11 and `numpy==2.5.3` on Python 3.12;
the latter no longer supports 3.11. Preserve both declared interpreter targets.
Qt dependencies are `PySide6_Addons==6.12.0`,
`PySide6_Essentials==6.12.0`, `shiboken6==6.12.0`,
`PySide6_Pdf==6.12.0.140` and `PySide6_WebEngine==6.12.0.140`.
The PDF/WebEngine distributions are dependencies of the published PySide6 wheel;
their presence does not introduce browser rendering into the application.
Regenerate hash locks with `python verification/resolve_native_locks.py` using uv.
Do not substitute mock SDKs or
hide requirements to evade a dependency gate. Pillow is an independent verifier
dependency, not required by the application. Network transport may use the
standard library; tests must inject bounded transport without live credentials.

Provide exact dependency inventory, import aliases (`pxr` for usd-core, `warp`
for warp-lang), complete transitive edges, and hashes of acquired target wheels
before execution admission. Generated code must not download or install packages.
Failure of the lifecycle to support a Python dependency lock is an unresolved
framework integration constraint, not permission to omit the lock.

Use Qt for the window and native SDKs for rendering, USD and physics. Separate
configuration, network, scene coordination and UI modules. Keep native imports
lazy and unit-testable boundaries explicit. Framework test and smoke modes must
use genuine portable behavior; they are not GPU acceptance. Generate native
integration and Qt UI tests as additional clearly named targets which fail on
missing required native facilities. Never mark them passed because they skipped.

Build/test helpers use the selected Python interpreter with bytecode writes
disabled, write derived artifacts outside `source/`, and never import generated
manifest data as an expected-results oracle. Use the desktop-wheels packaging
profile without a competing Make profile. Its tree export contains application
modules, framework test modes and independently verified retained dependencies.

The retained desktop provides `python desktop/manage.py setup|doctor|run|test`,
plus `warmup`, `install`, `uninstall` and `package`.
Setup creates a project-local virtual environment and installs the declared
native dependency closure with required archive hashes; it does not change global
Python or drivers. Before reporting setup complete, a bounded native warmup
authors a temporary default scene, renders meaningful pixels and shuts down,
so first-install shader preparation happens during setup. Warmup may take up to
five minutes and must report failures; it does not replace full acceptance or
weaken the 90-second application first-frame test. Doctor
reports exact dependency versions, platform eligibility and driver availability,
including a conflicting USD provider, without claiming rendered acceptance.
Run opens the real application and accepts an optional `--scene` local path.
Test runs the complete native and Qt suite and propagates failures.
Install creates a per-user desktop/Start Menu launcher. Uninstall removes only
the unchanged launcher owned by this checkout, preserving documents and the
runtime directory. Package creates a deterministic source/setup ZIP and checksum
with dependency locks and native fixtures; it must not include credentials,
environments, caches or private worker configuration. This prototype bundle is
distinct from a verifier-admitted release artifact.

#### Scenario: Native desktop target is admitted

- **WHEN** the declared packages and complete dependency evidence are available on a supported NVIDIA target
- **THEN** the generated application opens a real Qt window and uses the native SDKs
- **AND** missing or unsupported dependency evidence prevents execution admission

#### Scenario: Portable defaults are tested on the bootstrap host

- **WHEN** the defaults command or portable test modes execute without native packages
- **THEN** they run the real configuration behavior without importing Qt or GPU SDKs
- **AND** they make no claim that native integration passed
