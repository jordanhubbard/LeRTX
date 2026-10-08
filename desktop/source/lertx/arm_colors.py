"""Shared role identity for Qt and runtime printed-part materials."""
DEFAULT_COLORS = {'leader': '#1FAD9E', 'follower': '#F2A31F'}
ROLE_NAMES = {'leader': 'Leader · hand-operated controller',
              'follower': 'Follower · robot hand'}


def role_color(profile, role):
    return profile.get('general', {}).get(role+'_color', DEFAULT_COLORS[role])


def apply_material_colors(stage, profile):
    from pxr import Gf, Usd, UsdShade
    from .robot import ROOTS
    for role, path in ROOTS.items():
        root = stage.GetPrimAtPath(path)
        if not root:
            continue
        color = role_color(profile, role).lstrip('#')
        # UI colors are sRGB; USD surface inputs are linear-light RGB.
        rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
        rgb = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
        for prim in Usd.PrimRange(root):
            if prim.IsA(UsdShade.Shader) and '3d_printed' in str(prim.GetPath()):
                diffuse = UsdShade.Shader(prim).GetInput('diffuseColor')
                if diffuse:
                    diffuse.DisconnectSource()
                    diffuse.Set(Gf.Vec3f(*rgb))
