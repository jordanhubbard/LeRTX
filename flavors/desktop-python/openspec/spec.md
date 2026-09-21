# Native Python desktop requirements

### Requirement: Native Python application and portable bootstrap

Implement `source/main.py` with callable `main(payload)` and the JSON argument
array wrapper from the selected application implementation skill. Use Python
3.11 or 3.12 for native GPU execution on Linux x86-64 and Windows x86-64. The
defaults command and portable tests must also run on the macOS bootstrap Python
without importing unavailable native packages. Native commands must reject an
unsupported host or Python ABI with an actionable error before SDK initialization.

Use these exact runtime distributions and declare them honestly in requirements
and the source SBOM: `ovrtx==0.5.0.377615`, `ovstage==0.2.0.377349`,
`newton==1.6.0`, `warp-lang==1.17.0`, `numpy==2.4.6`, `usd-core==25.11`,
`PySide6==6.10.2`. Qt dependencies are `PySide6_Addons==6.10.2`,
`PySide6_Essentials==6.10.2`, `shiboken6==6.10.2`. Do not substitute mock SDKs or
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

#### Scenario: Native desktop target is admitted

- **WHEN** the declared packages and complete dependency evidence are available on a supported NVIDIA target
- **THEN** the generated application opens a real Qt window and uses the native SDKs
- **AND** missing or unsupported dependency evidence prevents execution admission

#### Scenario: Portable defaults are tested on the bootstrap host

- **WHEN** the defaults command or portable test modes execute without native packages
- **THEN** they run the real configuration behavior without importing Qt or GPU SDKs
- **AND** they make no claim that native integration passed
