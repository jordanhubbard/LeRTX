"""Run Linux native modules serially, each in its own contained SDK process.

Run with the installed application interpreter. Qt display configuration comes
from the caller. Cached shaders may be reused; this is not cold-cache acceptance.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

MODULES = (
    'test_launch_native', 'test_native_integration', 'test_physics_native',
    'test_robot_dynamics', 'test_runtime_native', 'test_robot_render_native',
    'test_window_native', 'test_reconstruction_native', 'test_photo_window_native',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('--memory-gib', type=float, default=12)
    parser.add_argument('--reserve-gib', type=float, default=16)
    parser.add_argument('--cpu-cores', type=int, default=2)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('This runner requires the Linux native resource guard')
    if min(args.timeout, args.memory_gib, args.reserve_gib, args.cpu_cores) <= 0:
        parser.error('Resource budgets must be positive')
    if args.output.exists():
        parser.error('Choose a new output directory to preserve prior evidence')
    args.output.mkdir(parents=True)
    scripts = Path(__file__).resolve().parent
    results = []
    for module in MODULES:
        started = time.monotonic()
        with (args.output/(module+'.log')).open('w') as log:
            result = subprocess.run([
                sys.executable, str(scripts/'native_guard.py'),
                '--report', str(args.output/(module+'-guard.json')),
                '--memory-gib', str(args.memory_gib),
                '--reserve-gib', str(args.reserve_gib),
                '--cpu-cores', str(args.cpu_cores),
                '--timeout', str(args.timeout), '--', sys.executable, '-u',
                str(scripts/'run_native_regression.py'), '--module', module,
            ], stdout=log, stderr=subprocess.STDOUT)
        results.append({'module': module, 'returncode': result.returncode,
                        'seconds': round(time.monotonic()-started, 3)})
        (args.output/'summary.json').write_text(json.dumps({
            'complete': len(results) == len(MODULES),
            'passed': len(results) == len(MODULES) and all(r['returncode'] == 0 for r in results),
            'cold_cache_tested': False, 'modules': results,
        }, indent=2)+'\n')
        print(module, result.returncode, flush=True)
    return 0 if all(r['returncode'] == 0 for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
