"""RTX picking and selection, executed only on the native scene owner."""


def pick(worker, u, v):
    import math
    import numpy as np
    import ovrtx
    if not all(math.isfinite(n) and 0 <= n < 1 for n in (u, v)):
        raise ValueError('Pick is outside the rendered image')
    if worker._gpu_index != 0:
        raise ValueError('Viewport picking requires CUDA-visible GPU 0 in this SDK')
    width = worker.profile['rendering']['width']
    height = worker.profile['rendering']['height']
    renderer = worker._renderer
    renderer.enqueue_pick_query('/Render/Product', u, v, min(1., u+1/width), min(1., v+1/height))
    products = renderer.step(render_products={'/Render/Product'}, delta_time=0., ordinal=worker._ordinal)
    frame = products['/Render/Product'].frames[0]
    mapping = frame.render_vars[ovrtx.OVRTX_RENDER_VAR_PICK_HIT].map(device=ovrtx.Device.CPU)
    try:
        magic = int(np.from_dlpack(mapping.params['magic']).reshape(-1)[0])
        version = int(np.from_dlpack(mapping.params['version']).reshape(-1)[0])
        count = int(np.from_dlpack(mapping.params['hitCount']).reshape(-1)[0])
        ids = np.from_dlpack(mapping['primPath']).copy().reshape(-1)
    finally:
        mapping.unmap()
    if magic != ovrtx.OVRTX_PICK_HIT_MAGIC or version != ovrtx.OVRTX_PICK_HIT_VERSION or not 0 <= count <= len(ids):
        raise RuntimeError('Unexpected native pick result')
    paths = [renderer.resolve_prim_path_id(int(i)) for i in ids[:count]]
    path = next((p for p in paths if p), None)
    return select(worker, path)


def select(worker, path):
    from pxr import Usd, UsdGeom
    from .joint_interaction import joint_for_path
    from .robot import joint_limits
    prim = worker.document.stage.GetPrimAtPath(path) if path else None
    paths = [str(p.GetPath()) for p in Usd.PrimRange(prim) if p.IsA(UsdGeom.Gprim)] if prim else []
    previous = getattr(worker, '_selected_meshes', [])
    if previous:
        worker._renderer.set_selection_outline_group_strings(previous, 0)
    if paths:
        worker._renderer.set_selection_outline_group_strings(paths, 1)
    # In the pinned attached-stage renderer, setting an outline group causes
    # descendant meshes to stop observing ancestor-only transform dirtiness.
    # Retain every touched mesh (including cleared selection) for explicit local
    # transform refresh when an ancestor moves. Never change authored USD.
    refresh = getattr(worker, '_selection_transform_refresh', {})
    for mesh in previous+paths:
        if mesh not in refresh:
            refresh[mesh] = UsdGeom.Xformable(worker.document.stage.GetPrimAtPath(mesh)).GetLocalTransformation()
    worker._selection_transform_refresh = refresh
    worker._selected_meshes = paths
    worker._cached_tick = None
    worker._settled_frames = 0
    result = {'path': path, 'joint': None}
    match = joint_for_path(worker.physics, path) if worker.physics and path else None
    if match:
        role, name, link = match
        low, high = joint_limits(role)[name]
        result['joint'] = dict(role=role, name=name, link=link, low=low, high=high,
            value=worker.physics.robot_positions()[role][name],
            locked=bool(worker._hardware_roles) or (role == 'follower' and worker.physics.following),
            lock_reason=('Disable physical live view before simulated manipulation.' if worker._hardware_roles
                         else 'Disable following in Robot Controls before dragging the follower.'))
    return result
