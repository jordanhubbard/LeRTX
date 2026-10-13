"""Resolve the declared native requirements into reproducible platform hash locks.

Requires uv. This reads public package metadata; it never installs or executes
the application. Runtime qualification is a separate gate.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _nvidia_requirements(requirements, provider):
    selected = []
    for line in requirements:
        if 'sys_platform == "darwin"' in line:
            continue
        if line.startswith(('usd-core==', 'usd-exchange==')):
            if line.startswith(provider + '=='):
                selected.append(line.split(';', 1)[0].strip())
        else:
            selected.append(line.split(';', 1)[0].strip() if 'sys_platform != "darwin"' in line else line)
    return selected


def _darwin_requirements(requirements):
    selected = []
    for line in requirements:
        if line.startswith(('ovrtx==', 'ovstage==')):
            continue
        if line.startswith(('usd-core==', 'usd-exchange==')):
            if line.startswith('usd-core=='):
                selected.append(line.split(';', 1)[0].strip())
        else:
            selected.append(line.split(';', 1)[0].strip() if 'sys_platform == "darwin"' in line else line)
    return selected


def _compile(inputs, output, extra):
    subprocess.run([
        'uv', 'pip', 'compile', str(inputs),
        '--python-version', '3.11', '--only-binary=:all:',
        '--find-links', str(ROOT/'desktop/wheels'), '--generate-hashes',
        '--no-annotate', '--no-header', '--output-file', str(output),
        *extra,
    ], check=True, stdout=subprocess.DEVNULL)
    return ('# Resolved native wheel closure; regenerate with '
            'verification/resolve_native_locks.py.\n' + output.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=ROOT/'desktop/locks')
    parser.add_argument('--targets', nargs='*', default=None,
                        help='Lock names to write (default: all NVIDIA and Darwin locks).')
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    wanted = None if args.targets is None else set(args.targets)
    requirements = (ROOT/'desktop/source/requirements.txt').read_text().splitlines()
    with tempfile.TemporaryDirectory(prefix='lertx-locks-') as directory:
        temporary = Path(directory)
        for provider, targets in [('usd-core', ('linux-x86_64', 'windows-x86_64')),
                                  ('usd-exchange', ('linux-arm64',))]:
            if wanted is not None and not wanted.intersection(targets):
                continue
            inputs, output = temporary/'requirements.in', temporary/'requirements.lock'
            inputs.write_text('\n'.join(_nvidia_requirements(requirements, provider))+'\n')
            text = _compile(inputs, output, [
                '--universal', '--index', 'https://pypi.nvidia.com',
            ])
            for target in targets:
                if wanted is None or target in wanted:
                    (args.output_directory/(target+'.txt')).write_text(text)
        darwin_targets = ('darwin-arm64', 'darwin-x86_64')
        if wanted is None or wanted.intersection(darwin_targets):
            inputs, output = temporary/'requirements.in', temporary/'requirements.lock'
            inputs.write_text('\n'.join(_darwin_requirements(requirements))+'\n')
            text = _compile(inputs, output, ['--universal'])
            for target in darwin_targets:
                if wanted is None or target in wanted:
                    (args.output_directory/(target+'.txt')).write_text(text)


if __name__ == '__main__':
    main()
