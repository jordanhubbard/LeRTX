"""Rebuild pinned SO-101 USD using NVIDIA's official URDF conversion route.

Run with: uv run --project desktop/tools desktop/tools/convert_robots.py
Conversion tools are isolated from the application SDK's USD distribution.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from pxr import Usd, UsdPhysics

RESOURCES = Path(__file__).resolve().parents[1] / 'source/lertx/resources/so101'
SKILLS_REVISION = 'd8519c57da6db5d9bea274ec1724a4a7a56a3dee'


def main():
    manifest = {'converter': 'urdf-usd-converter',
                'version': importlib.metadata.version('urdf-usd-converter'),
                'options': ['--no-layer-structure', '--no-physics-scene'],
                'skills_revision': SKILLS_REVISION, 'files': {}, 'adaptations': []}
    for role, filename in [('leader', 'so101_leader_new_calib.urdf'),
                           ('follower', 'so101_new_calib.urdf')]:
        source = RESOURCES / filename
        root = ET.parse(source).getroot()
        with tempfile.TemporaryDirectory() as output:
            subprocess.run(['urdf_usd_converter', str(source), output, *manifest['options']], check=True)
            stage = Usd.Stage.Open(str(Path(output) / (source.stem + '.usdc')))
            # A negligible-mass fixed tool frame is a coordinate marker, not a rigid body.
            # Preserve its transform and name without introducing invalid inertia.
            for link in root.findall('link'):
                if link.findall('visual') or link.findall('collision'):
                    continue
                inertial = link.find('inertial')
                if inertial is not None and (float(inertial.find('mass').get('value')) > 1e-9 or any(float(v) != 0 for v in inertial.find('inertia').attrib.values())):
                    continue
                matches = [p for p in stage.Traverse() if p.GetName() == link.get('name')]
                for prim in matches:
                    if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                        continue
                    for joint in list(stage.Traverse()):
                        if joint.IsA(UsdPhysics.FixedJoint) and prim.GetPath() in UsdPhysics.Joint(joint).GetBody1Rel().GetTargets():
                            stage.RemovePrim(joint.GetPath())
                    prim.RemoveAPI(UsdPhysics.RigidBodyAPI)
                    prim.RemoveAPI(UsdPhysics.MassAPI)
                    for prop in list(prim.GetProperties()):
                        if prop.GetName().startswith('physics:'):
                            prim.RemoveProperty(prop.GetName())
                    manifest['adaptations'].append({'role': role, 'link': link.get('name'),
                        'action': 'retain negligible-mass fixed tool frame as Xform, remove invalid rigid body and fixed joint'})
            target = RESOURCES / (role + '.usdc')
            stage.GetRootLayer().Export(str(target))
            manifest['files'][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (RESOURCES / 'usd-provenance.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
