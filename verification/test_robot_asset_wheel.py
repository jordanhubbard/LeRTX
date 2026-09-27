import importlib.util,tempfile,unittest,zipfile
from pathlib import Path
from robot_asset_wheel import build,verify

class ResourceWheelTests(unittest.TestCase):
    def test_repeatable_archive_preserves_every_resource_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);resources=root/'resources';resources.mkdir()
            for n in ('leader.usdc','follower.usdc','provenance.json','LICENSE'):(resources/n).write_bytes(b'\x00\xff exact model '+n.encode())
            first=root/'one.whl';second=root/'two.whl'
            self.assertEqual(build(resources,first),build(resources,second))
            self.assertEqual(verify(resources,first),4)
            (resources/'leader.usdc').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'differ'):verify(resources,first)

    def test_actual_model_tree_matches_packaged_dependency(self):
        root=Path(__file__).resolve().parents[1]
        self.assertGreater(verify(root/'desktop/source/lertx/resources/so101',root/'desktop/wheels/lertx_robot_assets-1.0.0-py3-none-any.whl'),20)

if __name__=='__main__':unittest.main()
