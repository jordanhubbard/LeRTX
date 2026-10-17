# macOS Metal renderer

- **Status:** completed
- **Owning queue item:** [MAC-001](active-work.md#mac-001-macos-metal-renderer-replacing-ovrtx)
- **Completion / archival evidence:** [Recorded MAC-001 host checks](active-work.md#mac-001-macos-metal-renderer-replacing-ovrtx): Darwin warmup passed on Apple M4 Pro (`native_warmup: passed`, 1.503s) without ovrtx/ovstage installed; `darwin-arm64.txt` pins usd-core, Newton, Warp, Qt and PyObjC Metal.

## Outcome

macOS is a native LeRTX target. The viewport is drawn with Metal. OVRTX and
OVStage are not installed, imported, or linked on Darwin. Linux and Windows keep
the pinned NVIDIA SDKs.

## Approach

`lertx.graphics` selects the backend. On Darwin it returns in-tree modules that
present the pinned public OVRTX/OVStage call sequence used by `NativeWorker`:
`RendererConfig`, `Renderer.attach_ovstage`, `population.open_usd`,
`write_attribute` of `omni:xform`, `advance_write_floor`, `step` with DLPack
CPU maps, picking constants, and destroy/detach. The Metal renderer reads the
OpenUSD stage through `usd-core`, tessellates visible gprims, and writes an
owned 8-bit framebuffer. Newton runs on Warp CPU; CUDA graphs are NVIDIA-only.

Darwin hash locks omit `ovrtx` and `ovstage`. They pin `usd-core`, Newton,
Warp, Qt, and PyObjC Metal. This is not an RTX/DLSS quality claim.
