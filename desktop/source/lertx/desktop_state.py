"""Nonsecret desktop state, independent of the inference profile."""
from pathlib import Path
import json
import os
import tempfile


def read_state(config_path):
    path=Path(config_path).with_name('desktop.json')
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value,dict):return {}
        return value
    except (OSError,ValueError):return {}


def save_state(config_path, changes):
    path=Path(config_path).with_name('desktop.json');path.parent.mkdir(parents=True,exist_ok=True)
    state=read_state(config_path);state.update(changes)
    fd,temp=tempfile.mkstemp(prefix='.desktop-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(state,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def remember_file(config_path, filename):
    path=str(Path(filename).resolve())
    old=read_state(config_path).get('recent',[])
    if not isinstance(old,list):old=[]
    save_state(config_path,{'recent':([path]+[p for p in old if isinstance(p,str) and p!=path])[:10]})
