"""Named joint-target presets (fractions of each joint's range) for the robot panel.

Fractions, not radians, are stored so a pose authored against one role's joint
limits still lands in range if limits differ slightly between leader and
follower calibration.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile

from .robot import JOINT_NAMES, ROLES

BUILTIN_DIR = Path(__file__).with_name('poses')


def user_poses_dir(config_path) -> Path:
    return Path(config_path).with_name('poses')


def _label_from_path(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        label = data.get('label')
        if isinstance(label, str) and label.strip():
            return label.strip()
    except (OSError, ValueError):
        pass
    return path.stem.replace('_', ' ').title()


def list_presets(config_path):
    """Return [(label, path, builtin)]: bundled presets first, then user-saved ones."""
    results = []
    if BUILTIN_DIR.is_dir():
        for path in sorted(BUILTIN_DIR.glob('*.json')):
            results.append((_label_from_path(path), path, True))
    user_dir = user_poses_dir(config_path)
    if user_dir.is_dir():
        for path in sorted(user_dir.glob('*.json')):
            results.append((_label_from_path(path), path, False))
    return results


def load_pose(path):
    """Return {'leader': {joint: fraction, ...}, 'follower': {...}}."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Unrecognized pose file')
    result = {}
    for role in ROLES:
        values = data.get(role)
        if not isinstance(values, dict):
            raise ValueError(f'Pose file is missing {role} joint values')
        fractions = {}
        for name in JOINT_NAMES:
            value = values.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0. <= value <= 1.:
                raise ValueError(f'Pose file has an invalid value for {role}.{name}')
            fractions[name] = float(value)
        result[role] = fractions
    return result


def save_pose(config_path, name, fractions) -> Path:
    """fractions: {'leader': {joint: 0..1, ...}, 'follower': {...}}."""
    name = (name or '').strip()
    if not name:
        raise ValueError('Choose a pose name')
    if any(c in name for c in '/\\'):
        raise ValueError('Pose names cannot contain / or \\')
    directory = user_poses_dir(config_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + '.json')
    data = {'schema': 1, 'label': name,
            'leader': {name_: fractions['leader'][name_] for name_ in JOINT_NAMES},
            'follower': {name_: fractions['follower'][name_] for name_ in JOINT_NAMES}}
    fd, temp = tempfile.mkstemp(prefix='.pose-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path
