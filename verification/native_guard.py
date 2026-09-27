#!/usr/bin/env python3
"""Contained Linux native qualification. Never launch a GPU test unguarded.

A cgroup limits charged process memory and swap. Unified GPU allocations may not
all be charged to that cgroup, so a separate host-headroom watchdog is mandatory.
This does not replace application-level resource isolation or performance tests.
"""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

GIB = 1024**3


def available_bytes():
    fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(fields['MemAvailable'].split()[0]) * 1024


def stop_owned_unit(unit):
    subprocess.run(['systemctl', '--user', 'kill', '--signal=SIGTERM', '--kill-whom=all', unit],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    # Do not block waiting for a GPU call to return before requesting termination.
    subprocess.run(['systemctl', '--user', 'kill', '--signal=SIGKILL', '--kill-whom=all', unit],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--memory-gib', type=float, default=8)
    parser.add_argument('--reserve-gib', type=float, default=16)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or min(args.memory_gib, args.reserve_gib, args.timeout) <= 0:
        parser.error('A command and positive resource budgets are required')
    report = {'status': 'blocked', 'memory_limit_bytes': int(args.memory_gib*GIB),
              'reserve_bytes': int(args.reserve_gib*GIB), 'swap_limit_bytes': 0,
              'timeout_seconds': args.timeout, 'launched': False}
    process = None
    lock = None
    unit = 'lertx-native-' + uuid.uuid4().hex + '.scope'
    try:
        if sys.platform != 'linux' or not Path('/sys/fs/cgroup/cgroup.controllers').is_file():
            raise RuntimeError('Native qualification requires Linux cgroup v2 containment')
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
        lock = (runtime/'lertx-native-qualification.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another native qualification process owns this host') from None
        available = available_bytes()
        report['initial_available_bytes'] = available
        if available < report['reserve_bytes'] + report['memory_limit_bytes']:
            raise RuntimeError('Insufficient headroom for the workload budget plus host reserve')
        # Scope preserves only the caller's existing environment; no copied
        # credentials, environment dump or permanent user-manager mutation.
        launch = ['systemd-run', '--user', '--scope', '--quiet', '--unit='+unit,
                  '-p', 'MemoryMax='+str(report['memory_limit_bytes']),
                  '-p', 'MemorySwapMax=0',
                  '-p', 'CPUQuota=200%', '-p', 'TasksMax=128',
                  '-p', 'RuntimeMaxSec='+str(args.timeout), '--', *command]
        start = time.monotonic()
        process = subprocess.Popen(launch, start_new_session=True)
        report.update(launched=True, status='running', minimum_available_bytes=available)
        while process.poll() is None:
            available = available_bytes()
            report['minimum_available_bytes'] = min(report['minimum_available_bytes'], available)
            if available < report['reserve_bytes'] or time.monotonic()-start > args.timeout:
                report['status'] = 'aborted'
                report['reason'] = 'host memory reserve exhausted' if available < report['reserve_bytes'] else 'deadline exceeded'
                stop_owned_unit(unit)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                break
            try: process.wait(timeout=.2)
            except subprocess.TimeoutExpired: pass
        report['seconds'] = round(time.monotonic()-start, 3)
        report['returncode'] = process.returncode
        if report['status'] == 'running':
            report['status'] = 'passed' if process.returncode == 0 else 'failed'
    except Exception as error:
        report['reason'] = str(error)
        if process is not None and process.poll() is None:
            stop_owned_unit(unit)
    finally:
        if lock is not None:
            lock.close()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    if report['status'] != 'passed':
        print('Native qualification '+report['status']+': '+report.get('reason', 'command failed'), file=sys.stderr)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
