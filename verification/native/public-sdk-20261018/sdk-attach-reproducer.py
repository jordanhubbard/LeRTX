import faulthandler,time
faulthandler.dump_traceback_later(30,repeat=True)
import ovrtx,ovstage
start=time.monotonic()
print('renderer-create',flush=True)
renderer=ovrtx.Renderer(config=ovrtx.RendererConfig(active_cuda_gpus='0',selection_outline_enabled=True,selection_outline_width=3,keep_system_alive=False))
print('renderer-created',time.monotonic()-start,flush=True)
stage=ovstage.Stage('bounded-sdk-diagnostic')
print('stage-created',time.monotonic()-start,flush=True)
renderer.attach_ovstage(stage)
print('stage-attached',time.monotonic()-start,flush=True)
renderer.destroy()
print('renderer-destroyed',time.monotonic()-start,flush=True)
