# Omarchy performance testing — 2026-09-26

The default 720p application now displays **29.95 fps** and
advances simulation at **99.67% of wall time**.
The baseline UI managed only 12.45 fps and
41.49% of wall time despite adequate renderer throughput.

Two measured faults were corrected: frame deadlines were based on completion
instead of start time, and runtime scene exports accumulated as large text USD
files. Frame scheduling now uses start-to-start elapsed time, idle polling slows
down, runtime snapshots use binary USD, and obsolete owned snapshots are removed
after the old renderer closes. One measured snapshot fell from 120,820,400 bytes
to 6,807,717 bytes. Reset already preserves the renderer from the preceding repair.

## Conditions and scope

- Omarchy Linux x86-64, RTX 5080 Laptop GPU, NVIDIA driver 610.57.04.
- CPU governor remained `powersave`; test CPU quota was 200% (two CPU equivalents).
  Some CPU throttling occurred in the initial run; these are contained-workload
  timings, not unrestricted hardware maximums.
- Balanced rendering; both SO-101 arms, colliders, work surface, obstacle and sphere;
  240 Hz physics with four substeps. Motion targets change during the native matrix.
- Sequential runs only. Each had an 8 GiB charged-memory cap, zero cgroup swap,
  a 16 GiB host reserve, and a deadline. No native work ran on Spark.
- Existing SDK shader/kernel caches. Startup numbers are cached-start observations,
  not first-ever installation or cold-cache results.
- Tested the current uncommitted worktree, not a new release artifact. Exact source
  hashes and package versions are in [the environment record](omarchy-performance-fixed-environment.json).

## Visible Qt application

The actual Wayland Qt window ran for 20 seconds at the 30 fps target.

| Measurement | Before | After |
|---|---:|---:|
| Displayed fps | 12.45 | 29.95 |
| Simulation / wall time | 41.49% | 99.67% |
| First frame | 7.71 s | 5.78 s |
| Frame interval p95 | 80.65 ms | 36.71 ms |

After the fix, the 20 ms Qt heartbeat had a maximum interval of
29.1 ms during playback. Paused CPU usage was
2.9% of one CPU over the five-second sample.
Paused native requests returned cached frames without simulation, inverse
kinematics or rendering after four settling frames.
[Before](omarchy-window.json), [after](omarchy-window-fixed.json),
[rendered window](omarchy-window-fixed.png).

## Renderer and simulation throughput

These are uncapped native-worker timings, excluding Qt presentation. Each frame
advances 1/30 second of simulation; they do not imply that the UI runs uncapped.
Runs lasted 20 seconds at 360p, 120 seconds at 720p, and 30 seconds at 1080p,
after warm-up. Raw frame durations are retained.

| Resolution | Frames | Throughput fps | p95 frame | p99 frame |
|---|---:|---:|---:|---:|
| 640×360 | 1037 | 51.9 | 20.1 ms | 21.4 ms |
| 1280×720 | 5464 | 45.6 | 22.7 ms | 23.4 ms |
| 1920×1080 | 1055 | 35.2 | 29.9 ms | 30.5 ms |

## Memory and scene lifecycle

Across the corrected measurements, process RSS high-water was **5.14 GiB**;
the highest sampled whole-GPU allocation was **2.15 GiB** (includes the small
pre-existing desktop allocation). Charged cgroup memory and process RSS differ
because shared mapped pages and file cache are accounted differently.
No cgroup swapping occurred. Minimum observed host headroom was **20.20 GiB**.
The 120-second 720p trace and repeated reset samples are retained in
[the corrected native matrix](omarchy-benchmark-fixed.json).

Ten resets averaged 838 ms excluding the following render.
Three reopens to first frame averaged 3.62 s,
compared with 5.66 s before compact snapshots.
The additional lifecycle run exercised ten further resets and ten reopens:

| Reopen | Process RSS MiB | Charged memory MiB | GPU MiB |
|---|---:|---:|---:|
| reopen-1 | 4910 | 3293 | 1957 |
| reopen-2 | 4832 | 3219 | 1959 |
| reopen-3 | 4891 | 3276 | 1963 |
| reopen-4 | 5100 | 3485 | 1965 |
| reopen-5 | 5142 | 3529 | 1969 |
| reopen-6 | 5169 | 3556 | 1971 |
| reopen-7 | 5206 | 3593 | 1975 |
| reopen-8 | 5260 | 3642 | 1977 |
| reopen-9 | 5259 | 3647 | 1983 |
| reopen-10 | 5205 | 3593 | 1985 |

The ten-reopen run still ends about 295 MiB higher in process RSS, 300 MiB higher
in charged memory and 28 MiB higher in GPU allocation than its first reopen.
Allocation varies between iterations; these observations do not establish the
precise owner or prove an unbounded leak. **Repeated-reopen retention remains
unresolved** despite removing accumulated snapshots.

[Lifecycle samples](omarchy-lifecycle.json) include idle, reset, reopen and shutdown
measurements. These bounded runs do not establish all-day leak freedom, large-scene
capacity, cold-cache startup or performance on Windows/Spark.

## Regression and failure record

All 11 focused runtime, robot rendering, Qt-window, idle, settings and mock-device
tests pass with the normal desktop initialization order:
[summary](regression-summary.txt), [guard result](omarchy-regression-qt-first-guard.json).

An earlier combined test process initialized headless OVRTX first and Qt later.
Its first two tests passed, but the Qt test crashed in `libEGL_nvidia` with exit 139.
The standalone Qt test passed, and the complete mixed suite passed when Qt was
initialized first, as in the desktop entry point. This late-Qt SDK initialization
failure is recorded, not counted as a clean pass or a fixed SDK defect.
[Failed-run containment result](omarchy-regression-failed-guard.json).

The guarded native matrix, window benchmark and focused regression are reproducible
with `verification/benchmark_native.py`, `verification/benchmark_window.py` and
`verification/run_native_regression.py`, respectively, through
`verification/native_guard.py`. Use the worker's native Wayland environment for
Qt runs. Do not overlap these runs or remove the resource guards.

## Additional raw evidence

[completion-audit](completion-audit.json), [omarchy-benchmark-cgroup](omarchy-benchmark-cgroup.json), [omarchy-benchmark-fixed-guard](omarchy-benchmark-fixed-guard.json), [omarchy-benchmark-guard](omarchy-benchmark-guard.json), [omarchy-benchmark](omarchy-benchmark.json), [omarchy-lifecycle-guard](omarchy-lifecycle-guard.json), [omarchy-performance-cleanup](omarchy-performance-cleanup.json), [omarchy-performance-environment](omarchy-performance-environment.json), [omarchy-window-fixed-guard](omarchy-window-fixed-guard.json), [omarchy-window-guard](omarchy-window-guard.json), [omarchy-window](omarchy-window.png).
