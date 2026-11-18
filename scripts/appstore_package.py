#!/usr/bin/env python3
"""Stage and package an already-verified ZIP for Nextcloud App Store signing.

No signing keys, network calls, GitHub mutations or Nextcloud instances are used.
The app files must be signed with Nextcloud's occ integrity:sign-app between
'stage' and 'package'. This is a structural/integrity gate, not a signature
or App Store approval substitute.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import pathlib
import re
import stat
import tarfile
import xml.etree.ElementTree as ET
import zipfile

APP_ID = 'passwords_otp'
SIGNATURE = 'appinfo/signature.json'
MAX_ARCHIVE = 20_000_000
MAX_UNPACKED = 30 * 1024 * 1024
MAX_FILES = 64
APP_DIRS = frozenset(('appinfo', 'lib', 'templates', 'css', 'js', 'img', 'l10n'))
ROOT_FILES = frozenset(('LICENSE', 'THIRD_PARTY_NOTICES.md',
                        'THIRD_PARTY_LICENSES.txt', 'BUILD.json'))


class PackageError(ValueError):
    pass


def digest(data: bytes, algorithm: str = 'sha256') -> str:
    return hashlib.new(algorithm, data).hexdigest()


def safe_path(name: str) -> bool:
    return (bool(name) and '\\' not in name and '\x00' not in name
            and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/')))


def allowed_source_path(name: str) -> bool:
    parts = name.split('/')
    return (safe_path(name) and all(not p.startswith('.') for p in parts)
            and (name in ROOT_FILES or (len(parts) > 1 and parts[0] in APP_DIRS)))


def source_files(archive: pathlib.Path, expected_sha256: str) -> tuple[dict[str, bytes], dict]:
    """Verify the existing, version-bound ZIP and its embedded BUILD.json."""
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise PackageError('Expected ZIP SHA256 must be a 64-digit lowercase hex digest')
    if archive.stat().st_size > MAX_ARCHIVE:
        raise PackageError('Source ZIP exceeds size limit')
    data = archive.read_bytes()
    if digest(data) != expected_sha256:
        raise PackageError('Source ZIP SHA256 mismatch')
    files: dict[str, bytes] = {}
    size = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if len(z.infolist()) > MAX_FILES:
            raise PackageError('Too many ZIP entries')
        for item in z.infolist():
            if not item.filename.startswith(APP_ID + '/'):
                raise PackageError('ZIP must contain only the app-id root')
            rel = item.filename[len(APP_ID) + 1:]
            mode = item.external_attr >> 16
            if (not allowed_source_path(rel) or rel in files or item.is_dir()
                    or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or item.flag_bits & 1):
                raise PackageError('Unsafe ZIP entry: ' + item.filename)
            size += item.file_size
            if size > MAX_UNPACKED:
                raise PackageError('ZIP expansion exceeds limit')
            files[rel] = z.read(item)
    if 'BUILD.json' not in files or 'appinfo/info.xml' not in files or SIGNATURE in files:
        raise PackageError('Missing metadata or unexpected pre-existing signature')
    manifest = json.loads(files['BUILD.json'])
    if not isinstance(manifest, dict) or manifest.get('app') != APP_ID:
        raise PackageError('Wrong application in BUILD.json')
    version = manifest.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise PackageError('Invalid application version')
    expected = manifest.get('files')
    if (not isinstance(expected, dict) or set(expected) != set(files) - {'BUILD.json'}
            or any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v)
                   or digest(files[k]) != v for k, v in expected.items())):
        raise PackageError('ZIP contents differ from BUILD.json file hashes')
    xml = files['appinfo/info.xml']
    if len(xml) > 512 * 1024 or b'<!doctype' in xml.lower():
        raise PackageError('Invalid appinfo size or XML doctype')
    info = ET.fromstring(xml)
    if (info.tag != 'info' or info.findtext('id') != APP_ID
            or info.findtext('version') != version or not info.findtext('bugs')):
        raise PackageError('Invalid App Store identity/version/bugs metadata')
    return files, manifest


def stage(archive: pathlib.Path, sha: str, destination: pathlib.Path) -> dict:
    files, manifest = source_files(archive, sha)
    if destination.exists() or destination.is_symlink():
        raise PackageError('Staging destination already exists; refusing overwrite')
    app = destination / APP_ID
    app.mkdir(parents=True, mode=0o755)
    for rel, data in sorted(files.items()):
        path = app / rel
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        with path.open('xb') as handle:
            handle.write(data)
        path.chmod(0o644)
    return manifest


def signed_files(app: pathlib.Path, originals: dict[str, bytes]) -> dict[str, bytes]:
    if app.name != APP_ID or app.is_symlink() or not app.is_dir():
        raise PackageError('Expected real signed app directory named ' + APP_ID)
    files: dict[str, bytes] = {}
    for path in app.rglob('*'):
        if path.is_symlink():
            raise PackageError('Symlink in signed stage')
        if path.is_dir():
            continue
        if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
            raise PackageError('Nonregular file in signed stage')
        rel = path.relative_to(app).as_posix()
        if not safe_path(rel) or rel in files:
            raise PackageError('Unsafe signed-stage filename')
        files[rel] = path.read_bytes()
    if set(files) != set(originals) | {SIGNATURE}:
        raise PackageError('Signed stage must contain original files plus signature.json only')
    if any(files[k] != v for k, v in originals.items()):
        raise PackageError('Application files changed after ZIP validation')
    try:
        signing = json.loads(files[SIGNATURE])
    except (ValueError, UnicodeError) as exc:
        raise PackageError('Invalid Nextcloud signature.json') from exc
    if not isinstance(signing, dict):
        raise PackageError('Invalid Nextcloud signature.json structure')
    cert, signature, hashes = (signing.get('certificate'), signing.get('signature'),
                               signing.get('hashes'))
    if (not isinstance(cert, str) or '-----BEGIN CERTIFICATE-----' not in cert
            or not isinstance(signature, str) or not signature
            or not isinstance(hashes, dict)):
        raise PackageError('Missing Nextcloud code-signing metadata')
    expected_hashes = {'/' + k: digest(v, 'sha512') for k, v in originals.items()}
    if hashes != expected_hashes:
        raise PackageError('Nextcloud code-signing hashes do not match signed stage')
    # This proves only hash-list consistency. Authenticity must be checked by
    # Nextcloud integrity:verify-app and by signed archive verification.
    return files


def tar_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
            dirs = {APP_ID + '/'}
            for rel in files:
                parents = pathlib.PurePosixPath(rel).parents
                dirs.update(APP_ID + '/' + str(p) + '/' for p in parents if str(p) != '.')
            for name in sorted(dirs):
                item = tarfile.TarInfo(name)
                item.type = tarfile.DIRTYPE
                item.mode = 0o755
                item.mtime = 0
                tar.addfile(item)
            for rel, data in sorted(files.items()):
                item = tarfile.TarInfo(APP_ID + '/' + rel)
                item.size = len(data)
                item.mode = 0o644
                item.mtime = 0
                tar.addfile(item, io.BytesIO(data))
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE:
        raise PackageError('App Store tar.gz exceeds 20 MB limit')
    return result


def verify_tar(data: bytes, files: dict[str, bytes]) -> None:
    seen = set()
    unpacked = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        for member in tar:
            if member.isdir() and member.name == APP_ID:
                continue
            if not member.name.startswith(APP_ID + '/'):
                raise PackageError('Invalid tar.gz top-level folder')
            rel = member.name[len(APP_ID) + 1:].rstrip('/')
            if member.isdir():
                if rel and not safe_path(rel):
                    raise PackageError('Invalid tar directory')
                continue
            if not member.isfile() or not safe_path(rel) or rel in seen:
                raise PackageError('Nonregular, duplicate or unsafe tar file')
            seen.add(rel)
            unpacked += member.size
            if unpacked > MAX_UNPACKED or rel not in files:
                raise PackageError('Unexpected or oversized tar file')
            handle = tar.extractfile(member)
            if handle is None or handle.read() != files[rel]:
                raise PackageError('Tar contents mismatch signed stage')
    if seen != set(files):
        raise PackageError('Missing files in App Store tar.gz')


def package(archive: pathlib.Path, sha: str, signed_app: pathlib.Path,
            destination: pathlib.Path) -> tuple[str, dict]:
    originals, manifest = source_files(archive, sha)
    files = signed_files(signed_app, originals)
    data = tar_bytes(files)
    verify_tar(data, files)
    if destination.exists() or destination.is_symlink():
        raise PackageError('Output exists; refusing overwrite')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as handle:
        handle.write(data)
    return digest(data), manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('stage', 'package'):
        p = sub.add_parser(command)
        p.add_argument('--zip', type=pathlib.Path, required=True)
        p.add_argument('--sha256', required=True, help='Independently verified ZIP SHA256')
        p.add_argument('--output', type=pathlib.Path, required=True)
        if command == 'package':
            p.add_argument('--signed-app-dir', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'stage':
            manifest = stage(args.zip, args.sha256, args.output)
            print('APPSTORE_STAGE_PASS version=' + manifest['version'] +
                  ' path=' + str(args.output / APP_ID))
            print('STOP: Sign the staged files with Nextcloud occ before packaging.')
        else:
            sha, manifest = package(args.zip, args.sha256, args.signed_app_dir, args.output)
            print('APPSTORE_ARCHIVE_PASS version=' + manifest['version'] +
                  ' sha256=' + sha + ' archive=' + str(args.output))
            print('NOT PUBLICATION-READY: verify Nextcloud signature and sign tar.gz externally.')
    except (PackageError, OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
        parser.exit(2, 'APPSTORE_STOP: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
