"""Local live diagnostics client: python -m lertx.debug_client --help."""
import argparse
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
from .config import user_config_dir


def request(session, path='/state', payload=None):
    # Discovery is local data, not permission to contact arbitrary hosts.
    from urllib.parse import urlsplit
    url = urlsplit(session['url'])
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port:
        raise ValueError('Invalid local diagnostic endpoint')
    req = urllib.request.Request(session['url']+path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization': 'Bearer '+session['token'], 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=7) as response:
            body = response.read()
            return body if response.headers.get_content_type() == 'image/png' else json.loads(body)
    except urllib.error.HTTPError as exc:
        with exc:
            body = exc.read()
            try:message = json.loads(body)['error']
            except (ValueError, KeyError):message = str(exc)
        raise ValueError(message) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['state', 'events', 'ui', 'frame', 'window', 'command', 'watch'])
    parser.add_argument('--pid', type=int)
    parser.add_argument('--window', help='Window id from state')
    parser.add_argument('--json', help='Validated command JSON')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    candidates = sorted((Path(user_config_dir())/'debug').glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
    if args.pid:
        candidates = [p for p in candidates if p.stem == str(args.pid)]
    session = None
    for path in candidates:
        try:
            candidate = json.loads(path.read_text(encoding='utf-8'))
            request(candidate)
            session = candidate
            break
        except (OSError, ValueError):
            continue
    if session is None:
        parser.error('No live session found. Launch with LERTX_DEBUG=1 and make run.')
    if args.action == 'watch':
        if not 0 < args.seconds <= 3600:
            parser.error('--seconds must be between 0 and 3600')
        stream = args.output.open('w', encoding='utf-8') if args.output else None
        try:
            end = time.monotonic()+args.seconds
            while time.monotonic() < end:
                value = json.dumps(request(session))
                print(value, file=stream, flush=True)
                time.sleep(.2)
        finally:
            if stream:stream.close()
        return
    path = '/window/'+str(args.window) if args.action == 'window' else '/'+args.action
    result = request(session, path, json.loads(args.json) if args.action == 'command' else None)
    if isinstance(result, bytes):
        if not args.output:parser.error('Image capture requires --output')
        args.output.write_bytes(result)
    else:
        value = json.dumps(result, indent=2)
        if args.output:args.output.write_text(value+'\n', encoding='utf-8')
        else:print(value)


if __name__ == '__main__':
    main()
