#!/usr/bin/env python3
"""Run pinned Nextcloud core components against the app's dependency lifecycle.

This is component integration with controlled service doubles, not a live server.
Official source downloads are opt-in and content hashes are checked before PHP
loads any file. The downloaded source stays outside the distributable package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name('nextcloud-35.0.2-sources.json')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--php', default='php', help='PHP 8.3–8.5 executable')
    parser.add_argument('--source-dir', type=Path, default=ROOT / '.build/nc35-lifecycle')
    parser.add_argument('--fetch-sources', action='store_true', help='Download missing official source files')
    parser.add_argument('--output', type=Path, default=ROOT / '.build/lifecycle-core/report.json')
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    if manifest['repository'] != 'nextcloud/server' or manifest['ref'] != 'v35.0.2':
        raise RuntimeError('Unexpected Nextcloud source reference')
    cache = args.source_dir.resolve()
    for relative, expected in manifest['files'].items():
        path = cache / relative
        if not path.resolve().is_relative_to(cache) or path.is_symlink():
            raise RuntimeError('Unsafe source cache path')
        if not path.is_file():
            if not args.fetch_sources:
                raise RuntimeError(f'Missing {relative}; use --fetch-sources once')
            url = f'https://raw.githubusercontent.com/nextcloud/server/v35.0.2/{relative}'
            with urlopen(url, timeout=30) as response:
                body = response.read(expected['bytes'] + 1)
            if len(body) != expected['bytes'] or digest(body) != expected['sha256']:
                raise RuntimeError(f'Official download differs from pinned source: {relative}')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        body = path.read_bytes()
        if len(body) != expected['bytes'] or digest(body) != expected['sha256']:
            raise RuntimeError(f'Source cache differs from pinned Nextcloud 35.0.2: {relative}')
    env = dict(os.environ, OTP_NC_SOURCE=str(cache))
    completed = subprocess.run([args.php, '-n', str(ROOT / 'tests/integration/core_lifecycle.php')],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0:
        raise RuntimeError('Core component integration failed:\n' + completed.stdout + completed.stderr)
    report = json.loads(completed.stdout)
    if report.get('status') != 'CORE_COMPONENT_PASS' or not report.get('cases'):
        raise RuntimeError('Missing core component pass report')
    if completed.stderr.strip():
        raise RuntimeError('Unexpected PHP diagnostics:\n' + completed.stderr)
    report['source_manifest_sha256'] = digest(MANIFEST.read_bytes())
    report['nextcloud_source_files_verified'] = len(manifest['files'])
    report['nextcloud_ref'] = manifest['ref']
    report['application_files'] = {
        str(path.relative_to(ROOT)): digest(path.read_bytes())
        for path in sorted([ROOT / 'appinfo/info.xml', *ROOT.glob('lib/**/*.php')])
    }
    report['test_files'] = {
        str(path.relative_to(ROOT)): digest(path.read_bytes())
        for path in [Path(__file__), ROOT / 'tests/integration/core_lifecycle.php']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f'CORE_COMPONENT_PASS cases={len(report["cases"])} php={report["php"]} '
          f'nextcloud={manifest["ref"]} source_files={len(manifest["files"])}')
    print('Scope: real core classes with service doubles; NOT live Nextcloud/Passwords acceptance')


if __name__ == '__main__':
    main()
