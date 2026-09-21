# Pinned native interfaces and review boundaries

These signatures were inspected against the pinned installed SDKs; the frame
mapping, publication, simulation and destruction sequence also passed actual GPU
probes. They constrain API use, not expected test outputs. Do not execute or copy
an external probe as application implementation.

## Renderer and runtime stage

Construct `ovrtx.Renderer(config=ovrtx.RendererConfig(...))`. Renderer has no
`device` keyword. GPU selection is `active_cuda_gpus=str(index)`; explicitly set
`keep_system_alive=False` on `RendererConfig` so destroying the last renderer
also ends its rendering-system lifetime. The pinned SDK otherwise retains that
system until process exit, which is not complete native worker shutdown.
On the worker, import `pxr.Usd` and create/release an anonymous
`Usd.Stage.CreateInMemory()` before constructing RTX. Import alone leaves USD
stage/plugin initialization lazy; existing-file launches need this bootstrap too.
For a document-driven scene session, defer renderer construction until the first
validated document and saved runtime USD snapshot are ready. Starting its command
thread must not create an empty renderer that the first scene rebuild immediately
destroys. First-scene startup constructs one renderer; later rebuilds and shutdown
still release the previous native resources on their owner thread.
Construct `ovstage.Stage(name)` and call `renderer.attach_ovstage(stage)`.
Population is the module function
`ovstage.population.open_usd(stage, absolute_usd_path, ordinal=n)`, not a Stage
method. Wait with `stage.advance_write_floor(n, ovstage.Scope.ALL).wait()`.
The filename must refer to a fully authored, saved local USD scene.

USD must contain a `UsdRender.Product`, its camera relationship, resolution and
ordered render-variable relationship. The `UsdRender.Var` uses source name
`LdrColor`. A `UsdRender.Settings` references the product and the stage metadata
`renderSettingsPrimPath` references those settings. A camera must actually face
the workspace: `Gf.Matrix4d().SetLookAt(eye, center, up).GetInverse()` is its
world transform. Apply materials using UsdPreviewSurface and a surface output;
provide real illumination. Define any missing application camera/render product
in a runtime/session layer when opening user scenes, not as destructive authored
changes to their source file.

`renderer.step(render_products={product_path}, delta_time=dt, ordinal=n)`
returns a dictionary. Iterate its values, then each `product.frames`. Select
`frame.render_vars[var_path]`; call `.map(device=ovrtx.Device.CPU)`.
`np.from_dlpack(mapped)` borrows memory. Copy the array while it is mapped,
release the borrowed view, and call `mapped.unmap()` in a finally-protected path.
Deliver only an owned image to Qt. Never cast the products dictionary to bytes.
Check actual dimensions, channel count and dtype rather than assuming all frames
are 1280x720. Keep the latest frame only, including the Qt delivery boundary.

All of those operations run on the native worker, including destruction.
Detach with `renderer.detach_ovstage()` (no argument), then `stage.destroy()`,
then `renderer.destroy()`. Resource creation may fail partially; cleanup must
still release each successfully created object. Reload releases old native and
Newton scene resources rather than accumulating scenes or stages.

## Newton construction and pose publication

Use `newton.ModelBuilder(up_axis=..., gravity=...)`. An application that converts
all input geometry into metric Z-up coordinates must also convert camera and
physics results back consistently. Otherwise preserve the authored up axis and
convert all physical lengths/velocities/gravity consistently with metersPerUnit.
Never silently treat Y-up or centimeter USD as metric Z-up.

`builder.add_body(xform=wp.transform(position, quaternion), label=prim_path)`
returns the actual integer body index. Record its USD prim mapping immediately.
`builder.add_shape_sphere(body_index, radius=radius, xform=...)` and
`builder.add_shape_box(body_index, hx=half_x, hy=half_y, hz=half_z, xform=...)`
add collision shapes; half extents are not full dimensions. For fixed shapes,
use body index `-1` with the world transform. The default work surface and obstacle
must both be actual collision geometry, not only visible objects or a substitute
infinite plane. Account for ancestor transforms, local shape offsets and scale.
Unsupported colliders, nonuniform sphere scale, shear, or nested rigid bodies
must produce an affected-prim diagnostic and disable scene simulation rather
than silently changing collision geometry.

Finalize with `builder.finalize(device="cuda:N")`; allocate `model.state()` twice,
`model.control()`, `newton.solvers.SolverXPBD(model)`,
`newton.CollisionPipeline(model)`, and `pipeline.contacts()` once per scene rebuild.
For each substep: clear forces on the current state; call
`pipeline.collide(state, contacts)`; call
`solver.step(state, next_state, control, contacts, dt)`; swap the states.
Neither `newton.SolverXPBD` nor `newton.body_prim_records` exists.

`state.body_q.numpy()` provides translation xyz and quaternion xyzw per body.
For a USD rotation use `Gf.Quatd(w, Gf.Vec3d(x,y,z))`; preserve geometry scale
when forming world matrices. Do not assume independent traversal and body arrays
have the same order, or that selected body indices are contiguous.

Construct `paths = ovstage.PathDictionary(stage)`;
`path_list = paths.create_path_list_from_strings(mapped_prim_paths)`;
`query = stage.query_from_path_list(path_list)`. Publish a matching ordered
NumPy array of float64 4x4 world matrices using
`stage.write_attribute(query, paths.intern_token("omni:xform"), ordinal=n,
tensors=matrices, is_array=False).wait()`. Then advance the write floor and render
the same ordinal. Camera changes use the same coordinator/ordinal sequence.
An empty matrix array does not publish motion.

## Reviewable application boundaries

Keep configuration validation/persistence, bounded inference transport, authored
USD editing, native coordination, and Qt presentation in separate modules. Native
imports stay lazy so defaults and configuration diagnostics work without SDKs.
Use a bounded worker-command queue and an owned latest-frame slot; do not run
an infinite Qt worker slot that starves its queued stop/control slots. A worker
thread may poll the command queue between native steps. Its failure must reach
the UI, clear readiness and trigger finally-based cleanup.

Implement and test each boundary before composing the main window: first pure
settings and transport; then authored scene and transform round trips; then
native stepping/publication/frames/cleanup; then every visible UI handler.
This ordering does not permit a partial deliverable. A source candidate must
contain the complete specified application and executable tests, with no inert
controls, hardcoded hierarchy, unconditional-pass tests or failure placeholders.
Test the actual visible buttons, editable fields, selection and worker error
delivery, not just helper functions. A native test must fail when GPU facilities
are absent, while portable tests remain explicitly separate.

#### Scenario: Live native scene follows Newton

- **WHEN** the native worker constructs supported bodies from an authored USD scene and advances simulation
- **THEN** exact mapped poses are published and actual owned RTX frames change
- **AND** pause preserves simulation time while camera frames continue, reset restores authored poses, and close joins after cleanup

#### Scenario: Editing and settings are real controls

- **WHEN** an operator edits an inspector transform or a staged settings field and saves
- **THEN** the corresponding scene or validated configuration changes and can be reloaded
- **AND** Cancel discards staged changes, failures remain actionable, and API keys never enter persisted data
