# Python dependency admission upstream work

- **Status:** active
- **Owning queue item:** [RENDER-001](active-work.md#render-001-milestone-two-ovrtx-ovstage-and-newton-application)
- **Completion / archival evidence:** pending supported dependency admission

## Downstream status

Upstream issue: [Litai #1](https://gitlab-master.nvidia.com/jordanh/literate-ai/-/issues/1).
The project-local parent checkout is `parents/literate-ai`, with local branch
`fix/python-lock-admission`; no branch has been pushed, merged or published.
Local draft commit: `dcacfbc243bb6c6c30c7e95ab079fa8ede5bf728`.

Latest integration: explicit wheel profiles now use the offline Standard
build/test/execute/cache path. Rebuild accepts an absolute operator wheel-directory
setting, verifies exact bytes before installation, and revalidates sealed artifact
and dependency evidence before execution. Current local regression: 374 tests,
372 passed and two existing platform skips; all 50 additional rebuild/CLI/
qualification-adapter tests pass. The patch remains local and unpublished.
Full framework qualification and actual Linux/Windows native dependency and
desktop acceptance remain outstanding. The full Python gate has been started
against this committed revision; no result is claimed before it finishes.

The earlier `4853ee67` source, exported and verified by archive hash, passes
209 focused dependency/runtime/Standard lifecycle tests on Linux x86-64 and
Python 3.11.16, with no skips (73.068 seconds). The environment was provisioned
through Make in a disposable test snapshot, not the existing SDK environment.
These are framework fixtures; real native SDK and desktop acceptance remain open.

Additional Linux rebuild/CLI/qualification regression attempt: 50 tests, 27
initialization errors. Source-only editable installation lacked exact Git origin;
building and installing a wheel with the exported commit's exact provenance
resolved that first prerequisite, but the worker cannot resolve the private
origin during lineage lookup. This remains a failed environment prerequisite,
not a CLI pass. No fake origin, network override or global installation was used.

Real Linux wheel archive validation now covers all ten pinned distributions:
nine pass, but `usd-core==25.11` fails conflicting duplicate Root-Is-Purelib
metadata. Newer 26.3 and 26.8 Linux CPython 3.11 wheels show the same defect.
The independent verifier and per-package evidence live at
`verification/native_wheels.py` and `verification/native/linux/wheel-archives.json`.
These checks execute no wheel code and do not establish installation or desktop
acceptance. A metadata-only repackaging proposal is awaiting operator direction;
the strict parent validator and original wheel bytes remain unchanged.

The Windows CPython 3.12 wheel for the same USD 25.11 pin has no conflicting
metadata and passes the unchanged archive validator. Its unmodified installation
in the disposable SDK environment passes the original native authoring/render/
physics probe. Evidence is retained under `verification/native/windows/`.
This does not resolve the Linux archive defect or full application admission.

The following records the earlier implementation stages; their then-pending
offline dispatch work is superseded by the integration result above.
The preparatory patch provides typed wheel-lock validation, exact wheel-byte and
metadata checks, and source-BOM graph projection tests. It does not yet enable
Standard admission. The parent design at `docs/roadmap/python-wheel-lock.md`
records the required controlled installation, cache and execution-evidence work.
Source preflight now binds the selected manifest to locked root requirements and
rejects undeclared dependency authorities. A consistent pair still cannot execute
without target-bound acquisition and installed-closure evidence.
Archive inspection now verifies WHEEL tags, complete RECORD hashes and portable
member paths, and retains native payload identities. A private staging context
copies and verifies incoming wheel streams, rejects changed staged files or link
aliases, and cleans partial copies on failure. Controlled network acquisition and
application execution admission are not yet implemented.
An explicit installed-tree observer now compares payload files to verified wheels,
checks installed RECORDs and emits dependency edges and import aliases without
importing packages. A real offline, hash-locked two-package pip installation passes
that observer. Selected-interpreter marker/tag observation is implemented
using an isolated probe and owned framework helper, including a test against a
clean target environment without packaging installed. The probe binds interpreter
and helper identities. The controlled installer now binds an exact pip wheel and
owned driver to that interpreter, installs offline, independently projects wrapper
and script-header changes, and revalidates installed payloads and target identity.
The current tests also cover obsolete wrapper removal, collisions, tampering,
cleanup and identical payload evidence across repeated installs. These are fixture
results, not desktop dependency admission: Standard build/profile and cache wiring,
network acquisition and native GPU dependency validation remain outstanding.
Retained artifact evidence now survives installer-context cleanup and requires an
independently sealed identity. The CycloneDX resolver can consume a fresh Standard
payload-verification callback, remap exact packages to source BOM references, and
check source imports against installed modules. Default resolution still refuses
Python locks; build flags and ambient observations cannot substitute for this
evidence. The public resolution port binds the installed-evidence identity.
The explicit Python wheel command profile now binds packaging Flavor, selected
interpreter, installer pin and source paths into the toolchain closure. It selects
isolated build/test/execute commands; local runtime tests import retained packages
without ambient site-packages or injected startup hooks. Standard acquisition and
build/cache dispatch must still create custody bindings from trusted lifecycle
records before desktop admission can proceed. Runtime assembly explicitly refuses
this target until that bridge exists, rather than using generic Python execution.
The focused tests passed 175 cases with the exact installer fixture and no skips;
another 22 application-port and CycloneDX regression tests passed;
an additional 148 profile/schema/runtime/lifecycle tests passed with two existing
platform-specific skips. Those skips cover macOS HTTP/SSE service acceptance and
a Linux-only JavaScript service process test. Profile selection tests for Linux
and Windows use host descriptions, not native GPU execution.
lint and formatting passed. The installed Litai distribution remains unchanged.
On the earlier draft, the broad Python suite was interrupted after 3,291 checkpointed cases, including
a passing self-hosting replay. No complete broad-suite pass is claimed.
Exact tested file hashes and the incomplete integration boundary are retained in
`verification/python-lock-review.json`.

Current upstream original-source SDK work is tracked in GitHub #407 and PR #438.
That stack is unmerged and is not proof of Python wheel admission for this app.
The Linux worker passed a fresh capacity/GPU check on resumption. Windows SSH
timed out on both bounded attempts; no new Windows installation was attempted.
The earlier connectivity recheck and retry returned network-unreachable. A later
IPv4 check recovered Windows SSH. RTX/OVStage binary installation now succeeds in
the disposable native probe environment. Two startup/cleanup cycles and two
fixed-fixture RTX/OVStage/Newton frame probes subsequently pass, with identical
repeat images and completed cleanup. Evidence lives in `verification/native/windows/`.
C: retains about 9.0 GiB free under disk warning. USD was not installed; the
probe loads the exact previously verified scene and does not test authoring/UI.
The USD archive defect and pending repair decision are unchanged. Linux remains
reachable with ample disk/RAM and an idle RTX 5090.

The installed Standard lifecycle rejects nonempty Python requirements and
pyproject dependencies with `dependencies.python-lock-unsupported`, and rejects
`uv.lock` with `dependencies.lock-authority-unsupported`. The relevant authority
is the parent dependency lock projection, not this application's product spec.
Do not remove manifests, hide imports, or weaken SBOM/acceptance checks.

Parent tracker inspection succeeded and a search for `Python dependency lock`
returned no issues. The operator has now authorized external issue filing and a
reviewable fix in a project-local parent checkout, without merging or publishing.
Native SDK probing
and specification/source generation can proceed, but desktop execution admission
must wait for supported complete dependency evidence.

The installed typed library-import mechanism was also inspected. It declares
native import names for generated library Components; it does not supply a
third-party package version, wheel-hash, or dependency-lock projection. It is
not an alternative admission route for the required Python distributions.

## Sanitized upstream title

Support complete typed Python dependency locks in the Standard lifecycle

## Sanitized upstream body

The Standard dependency acquisition projection rejects all nonempty Python
requirements and pyproject dependency declarations, as well as uv.lock. This
prevents admission of an otherwise valid generated Python application that
requires third-party distributions.

Please support a deterministic Python lock representation containing exact
distribution versions, target ABI/platform and marker selection, wheel hashes,
direct and transitive parent edges, and package-to-import aliases. Reconcile the
lock with the source BOM and resolved installed dependency graph. Reject missing
edges, hash drift, unsupported targets, and undisclosed packages. Do not treat a
flat requirements list as complete dependency provenance.

A portable upstream fixture can use one pure-Python root dependency with a
transitive dependency, plus target-marker and wheel-hash mismatch cases. Tests
should exercise initial generation, cache reuse, dependency acquisition and
artifact execution admission without introducing product-specific data.
