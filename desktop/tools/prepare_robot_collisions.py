"""Build deterministic per-part convex collision hulls (SciPy 1.17.1, NumPy 2.4.6)."""
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from scipy.spatial import ConvexHull

root=Path(__file__).resolve().parents[1]/'source/lertx/resources/so101'
output={}
for path in sorted((root/'assets').glob('*.stl')):
    data=path.read_bytes(); count=struct.unpack_from('<I',data,80)[0]
    if len(data)!=84+count*50:raise ValueError(path.name)
    dtype=np.dtype([('normal','<f4',(3,)),('points','<f4',(3,3)),('attribute','<u2')])
    points=np.unique(np.frombuffer(data,dtype=dtype,offset=84)['points'].reshape(-1,3),axis=0)
    hull=ConvexHull(points)
    selected=np.unique(hull.simplices); vertices=points[selected]
    lookup={int(old):new for new,old in enumerate(selected)}
    faces=[]
    for simplex,equation in zip(hull.simplices,hull.equations):
        face=[lookup[int(i)] for i in simplex]
        a,b,c=vertices[face]
        if np.dot(np.cross(b-a,c-a),equation[:3])<0:face[1],face[2]=face[2],face[1]
        start=face.index(min(face));faces.append(face[start:]+face[:start])
    output['assets/'+path.name]={'source_sha256':hashlib.sha256(data).hexdigest(),'vertices':vertices.tolist(),'triangles':sorted(faces)}
(root/'collision-hulls.json').write_text(json.dumps({'generator':'SciPy 1.17.1 ConvexHull; outward-wound per-part hulls','parts':output},sort_keys=True,separators=(',',':'))+'\n')
print(len(output),'collision hulls')
