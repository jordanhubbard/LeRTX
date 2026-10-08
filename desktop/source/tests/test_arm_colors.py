import copy,json,tempfile,unittest
from pathlib import Path
from lertx.config import DEFAULT_PROFILE,load_profile,save_profile,validate_profile
from lertx.arm_colors import apply_material_colors,role_color


class ArmColorTests(unittest.TestCase):
    def test_legacy_profile_retains_other_preferences(self):
        profile=copy.deepcopy(DEFAULT_PROFILE)
        del profile['general']['leader_color'];del profile['general']['follower_color']
        profile['general']['theme']='light';profile['rendering']['width']=640
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';path.write_text(json.dumps(profile))
            loaded=load_profile(str(path))
            self.assertEqual(loaded['general']['theme'],'light')
            self.assertEqual(loaded['rendering']['width'],640)
            self.assertEqual(role_color(loaded,'leader'),'#1FAD9E')
            loaded['general']['leader_color']='#8040c0';save_profile(loaded,str(path))
            self.assertEqual(load_profile(str(path)),loaded)

    def test_invalid_colors_are_rejected(self):
        for color in ('red','#fff','#12345678','url(x)',42):
            profile=copy.deepcopy(DEFAULT_PROFILE);profile['general']['leader_color']=color
            self.assertEqual(validate_profile(profile)['errors'],['general.leader_color'])

    def test_runtime_materials_follow_roles_and_leave_metal_alone(self):
        from pxr import Usd,UsdGeom,UsdShade,Sdf
        from lertx.robot import ROOTS
        stage=Usd.Stage.CreateInMemory();profile=copy.deepcopy(DEFAULT_PROFILE)
        profile['general'].update(leader_color='#ff0000',follower_color='#0000ff')
        for role,root in ROOTS.items():
            UsdGeom.Xform.Define(stage,root)
            for name in ('plastic_3d_printed','metal'):
                shader=UsdShade.Shader.Define(stage,root+'/Looks/'+name)
                shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set((.5,.5,.5))
        apply_material_colors(stage,profile)
        for role,root in ROOTS.items():
            self.assertEqual(tuple(UsdShade.Shader(stage.GetPrimAtPath(root+'/Looks/plastic_3d_printed')).GetInput('diffuseColor').Get()),
                             (1.,0.,0.) if role=='leader' else (0.,0.,1.))
            self.assertEqual(tuple(UsdShade.Shader(stage.GetPrimAtPath(root+'/Looks/metal')).GetInput('diffuseColor').Get()),(.5,.5,.5))
