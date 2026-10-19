# Current public SDK continuation

I fetched upstream and proved that `0ac4c58` is already an ancestor of SDK candidate `c835ea0`. There are no missing upstream commits to replay. The current 151 application-source files match the prior macOS qualification exactly.

I reran the current Metal/Newton 1.7 suite on macOS: all 346 tests pass in 145.690 seconds. Reproducible source packaging and extracted-package defaults pass. These results do not establish Windows or Linux NVIDIA readiness.

I prepared an isolated exact Git/LFS checkout and hash-locked SDK runtime on another Linux RTX 5090 worker after the original Linux GPU worker exhausted its disk/shared-memory headroom. The Windows L40 worker has only 6.3 GiB free, under 2%; a bounded cache survey finds about 208 MiB of caches. No files were deleted. The alternate Windows worker has space but no detected NVIDIA adapter, so it cannot replace native GPU evidence.

The alternate Linux runtime contains OVRTX 0.6.0.1791947691, OVStage 0.3.0.1791986420, Newton 1.7.0, NumPy 2.4.6 and Qt 6.12.0 under Python 3.11.16, with NVIDIA driver 595.84. The complete native suite now passes: 18 tests across all nine modules from exact commit `97bec1e`, under the regular two-core/12-GiB limits with prepared caches. Initial failures and diagnosis:

- The normal guarded CLI launch aborts with a native `std::system_error` saying resources are temporarily unavailable. BLAS/OpenMP thread limits alone do not fix it.
- Two-CPU affinity avoids that immediate allocation abort, but the unchanged launch deadline expires inside `attach_ovstage`.
- An explicit installation warmup with eight CPUs reaches the 12-GiB cgroup limit and is OOM-killed after 154.140 seconds. The host remains healthy; this is not a successful warmup.
- A small renderer/empty-stage program reproduces an attachment timeout with a display connection. A second control removes Qt, Newton and external USD and still times out. Renderer creation itself takes about four seconds.

I retain failed guards, scrubbed logs and the exact minimal reproducer. Original log hashes identify private retained originals; removal of local paths/session identifiers from committed logs changes their hashes deliberately. The separate five-minute/24-GiB bare-SDK diagnostic passes: attachment completes in 178.848 seconds and cleanup in 180.780 seconds. Actual application warmup then passes in 94.721 seconds with a meaningful frame and cleanup. The original prepared-cache launch passes in 7.162 seconds at the unchanged two-core/12-GiB budget. These results disprove a persistent attachment deadlock; they do not establish cold-cache performance or a portable memory minimum. The guard now bounds child affinity to its CPU quota while restoring its supervisor mask, and the complete native suite passes with that exact implementation.

The desktop source binding is refreshed only after this complete native pass; portable release checks pass (330 tests across 42 module runs), including robot asset wheel checks and reproducible packaging. Framework authority and locks pass, while the receipt is stale. The parent fix for target-bound source projection has landed in Literate AI PR 71 but is not in a published release: the current published pin remains 1.2.0. I improve CI failure output without changing its failure status. PR 27 remains draft until exact native and verifier-owned acceptance gates pass.
