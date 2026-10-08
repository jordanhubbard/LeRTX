"""Build and verify the offline robot-resource wheel without converting model bytes."""
import argparse,base64,csv,hashlib,io,json,zipfile
from pathlib import Path

NAME='lertx_robot_assets'
VERSION='1.0.0'
FILENAME=f'{NAME}-{VERSION}-py3-none-any.whl'
PREFIX=NAME+'/so101/'


def resource_files(root):
    result={}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():raise ValueError('Resource links are not permitted')
        if path.is_file():result[path.relative_to(root).as_posix()]=path.read_bytes()
    if not result or not {'leader.usdc','follower.usdc','provenance.json','LICENSE'}<=result.keys():
        raise ValueError('Incomplete robot resource tree')
    return result


def build(root,destination):
    resources=resource_files(root);dist=f'{NAME}-{VERSION}.dist-info'
    files={PREFIX+n:data for n,data in resources.items()}
    files[NAME+'/__init__.py']=b'"""Exact packaged SO-101 resources; no runtime acquisition or conversion."""\n'
    files[dist+'/METADATA']=b'Metadata-Version: 2.1\nName: lertx-robot-assets\nVersion: 1.0.0\nSummary: Pinned SO-101 models and provenance for LeRTX\nRequires-Python: >=3.11\nLicense: Apache-2.0\n\n'
    files[dist+'/WHEEL']=b'Wheel-Version: 1.0\nGenerator: lertx-resource-builder\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    files[dist+'/top_level.txt']=(NAME+'\n').encode()
    record=io.StringIO(newline='');writer=csv.writer(record,lineterminator='\n')
    for name,data in sorted(files.items()):writer.writerow([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)])
    writer.writerow([dist+'/RECORD','','']);files[dist+'/RECORD']=record.getvalue().encode()
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            entry=zipfile.ZipInfo(name,(2026,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16
            archive.writestr(entry,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    verify(root,destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def verify(root,wheel):
    resources=resource_files(root)
    with zipfile.ZipFile(wheel) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate wheel entries')
        actual={n[len(PREFIX):]:archive.read(n) for n in names if n.startswith(PREFIX)}
        if actual!=resources:raise ValueError('Packaged robot resources differ from the reviewed source tree')
    return len(resources)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources',type=Path,default=Path('desktop/source/lertx/resources/so101'))
    parser.add_argument('--output',type=Path,default=Path('desktop/wheels')/FILENAME)
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:print(json.dumps({'resource_files':verify(args.resources,args.output),'verified':True}))
    else:print(json.dumps({'wheel':str(args.output),'sha256':build(args.resources,args.output)}))
