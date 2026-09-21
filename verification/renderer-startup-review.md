# Deferred renderer startup repair

Date: 2026-09-18 (local), 2026-09-19 UTC.

The packaged-adoption development suite exposed another existing-file launch
timeout. Its trace stopped in renderer destruction during the first rebuild.
`SceneWorker` inherited eager renderer initialization, then immediately destroyed
that unused instance to open its first document. The command thread now starts
without a renderer; `rebuild()` initializes it after preparing the runtime USD.
The anonymous OpenUSD bootstrap and explicit renderer-system shutdown remain.

The portable regression failed before the repair (one unexpected initialization)
and passes after it. Real CLI tests now additionally require exactly one native
initialization, while still requiring a displayed native frame and clean shutdown.
The 90-second first-frame and 150-second subprocess deadlines are unchanged.
The Flavor native-interface contract records this lifecycle requirement.

## Verification

- macOS: four portable worker tests pass (0.116 seconds).
- Linux RTX 5090: three native launch tests pass (21.795 seconds).
- Linux RTX 5090: all 158 desktop tests pass (82.543 seconds), no skips.
- Linux: three additional independent existing-file launches pass (6.378,
  6.373 and 6.498 seconds). These are fresh processes, not cleared shader caches.
- Windows L40: all eight launch, worker and native-runtime tests pass
  (205.942 seconds), including real frames, physics, editing, saving and close.
  The SSH transport disconnected, but a subsequent read recovered the completed
  worker log with all eight tests passing and the runner's final free-space line.
- Windows ran against its existing SDK with a monitored 2 GiB reserve and
  256 MiB write budget; final free space was 4,701,831,168 bytes. No cleanup or
  SDK installation was performed; the inspected pip cache contained only 98 bytes.

Linux used an isolated task-owned source snapshot; a post-test checksum-based
rsync comparison found no differences. Windows used a separately extracted
snapshot from the source archive identified below. Private worker paths remain
in ignored local logs. No existing
interactive application was restarted or replaced.

Local logs: `_build/renderer-startup-full.stderr.log`,
`_build/renderer-startup-launch.stderr.log`, `_build/renderer-startup-windows.log`.
Original failure evidence remains in
`verification/native/linux/package-adoption-regression.json`.

## Tested source hashes (SHA-256)

| File | Hash |
| --- | --- |
| desktop/source/lertx/runtime.py | 959317832b8ba78d5718f9aca5f8c3c85b5d8b67c1c3fb987705431bec7b1655 |
| desktop/source/tests/test_worker.py | 3c4a58e766ba31fa452e0118e77797143e61280bd2cd0aff2e663eb50586bdbf |
| desktop/source/tests/test_launch_native.py | 0b12746a0ede6a6a01d982caaf3686ff6cd6ff9d78d6ee27c89885ae983da97a |
| Windows source archive | f7c3a37287ca20a8899d327b416d0101a879b5e8329c9b68b48eed474f7b7527 |

## Boundaries

These are development-source regressions, not installed-product acceptance.
The separate parent package-count fix is untouched. No admission, lifecycle
rebind, receipt refresh, merge or release is claimed. Windows full-suite testing
was not repeated for this snapshot. The workspace has no Git remote, so forge
survey and remote landing are unavailable. Retained-source workflow kept the
specification contract aligned with the repair without bypassing acceptance.
