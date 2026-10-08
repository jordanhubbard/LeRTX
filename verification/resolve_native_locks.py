"""Resolve the declared native requirements into reproducible platform hash locks.

Requires uv. This reads public package metadata; it never installs or executes
the application. Runtime qualification is a separate gate.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=ROOT/'desktop/locks')
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    requirements = (ROOT/'desktop/source/requirements.txt').read_text().splitlines()
    with tempfile.TemporaryDirectory(prefix='lertx-locks-') as directory:
        temporary = Path(directory)
        for provider, targets in [('usd-core', ('linux-x86_64', 'windows-x86_64')),
                                  ('usd-exchange', ('linux-arm64',))]:
            selected = []
            for line in requirements:
                if line.startswith(('usd-core==', 'usd-exchange==')):
                    if line.startswith(provider+'=='):
                        selected.append(line.split(';', 1)[0].strip())
                else:
                    selected.append(line)
            inputs, output = temporary/'requirements.in', temporary/'requirements.lock'
            inputs.write_text('\n'.join(selected)+'\n')
            subprocess.run([
                'uv', 'pip', 'compile', str(inputs), '--universal',
                '--python-version', '3.11', '--only-binary=:all:',
                '--index', 'https://pypi.nvidia.com',
                '--find-links', str(ROOT/'desktop/wheels'), '--generate-hashes',
                '--no-annotate', '--no-header', '--output-file', str(output),
            ], check=True, stdout=subprocess.DEVNULL)
            text = ('# Resolved native wheel closure; regenerate with '
                    'verification/resolve_native_locks.py.\n'+output.read_text())
            for target in targets:
                (args.output_directory/(target+'.txt')).write_text(text)


if __name__ == '__main__':
    main()
