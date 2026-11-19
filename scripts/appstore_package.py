#!/usr/bin/env python3
"""Deterministic Nextcloud tar.gz distribution and explicit signing gates.

The ordinary archive is an unsigned manual-installation artifact. Signing is
deliberately separate: stage exact ZIP bytes, use occ integrity:sign-app, then
package only after a real Nextcloud integrity:check-app succeeds. This script
never reads a private signing key or uploads a release.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import io
import json
import pathlib
import re
import stat
import subprocess
import tarfile
import tempfile
import zipfile

APP_ID = 'passwords_otp'
SIGNATURE = 'appinfo/signature.json'
MAX_ARCHIVE = 20_000_000
MAX_UNPACKED = 30 * 1024 * 1024
MAX_FILES = 512
MAX_SIGNATURE = 256 * 1024
STAMP = 0


class PackageError(ValueError):
    pass


def digest(data: bytes, algorithm: str = 'sha256') -> str:
    return hashlib.new(algorithm, data).hexdigest()


def safe_path(name: str) -> bool:
    # Runtime paths are deliberately ASCII. This also makes PHP's signed JSON
    # encoding unambiguous; no Unicode normalization or platform separators.
    return (isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9_./-]+', name))
            and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PackageError('Duplicate JSON key')
        result[key] = value
    return result


def read_regular(path: pathlib.Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise PackageError('Expected a regular file: ' + str(path))
    if path.stat().st_size > limit:
        raise PackageError('File exceeds size limit: ' + str(path))
    with path.open('rb') as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise PackageError('File exceeds size limit: ' + str(path))
    return data


def source_files(archive: pathlib.Path, sha256: str) -> tuple[dict[str, bytes], dict]:
    # Reuse the current release's exact allowlist, version and BUILD.json gate.
    # The lazy import avoids a cycle when release.py creates the ordinary TAR.
    import release
    data = read_regular(archive, MAX_ARCHIVE)
    try:
        files, manifest = release.validate_package(data, sha256)
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        raise PackageError('Source ZIP validation failed: ' + str(exc)) from exc
    if SIGNATURE in files:
        raise PackageError('Source ZIP must not contain a pre-existing signature')
    return files, manifest


def expected_directories(files: dict[str, bytes]) -> set[str]:
    directories = {APP_ID}
    for rel in files:
        directories.update(APP_ID + '/' + str(parent)
                           for parent in pathlib.PurePosixPath(rel).parents
                           if str(parent) != '.')
    return directories


def validate_files(files: dict[str, bytes]) -> None:
    if not files or len(files) > MAX_FILES:
        raise PackageError('Invalid runtime file count')
    if any(not safe_path(path) or not isinstance(data, bytes) for path, data in files.items()):
        raise PackageError('Invalid runtime path or content')
    if sum(map(len, files.values())) > MAX_UNPACKED:
        raise PackageError('Unpacked size limit exceeded')
    if not {'appinfo/info.xml', 'BUILD.json'} <= files.keys():
        raise PackageError('Missing runtime metadata')


def tar_bytes(files: dict[str, bytes]) -> bytes:
    validate_files(files)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=STAMP, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
            for name in sorted(expected_directories(files)):
                entry = tarfile.TarInfo(name + '/')
                entry.type = tarfile.DIRTYPE
                entry.mode = 0o755
                entry.mtime = STAMP
                tar.addfile(entry)
            for rel, data in sorted(files.items()):
                entry = tarfile.TarInfo(APP_ID + '/' + rel)
                entry.size = len(data)
                entry.mode = 0o644
                entry.mtime = STAMP
                tar.addfile(entry, io.BytesIO(data))
    data = output.getvalue()
    if len(data) > MAX_ARCHIVE:
        raise PackageError('tar.gz exceeds the App Store 20 MB limit')
    return data


def verify_tar(data: bytes, files: dict[str, bytes]) -> None:
    """Check without extraction, including duplicate/link/traversal entries."""
    validate_files(files)
    if not data or len(data) > MAX_ARCHIVE:
        raise PackageError('Archive size limit exceeded')
    max_tar = MAX_UNPACKED + MAX_FILES * 1024 + 10240
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as gz:
            raw = gz.read(max_tar + 1)
        if len(raw) > max_tar:
            raise PackageError('Tar expansion exceeds size limit')
        expected_dirs = expected_directories(files)
        seen_files: set[str] = set()
        seen_dirs: set[str] = set()
        total = 0
        end = 0
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tar:
            for entry in tar:
                if (entry.pax_headers or entry.uid != 0 or entry.gid != 0
                        or entry.uname or entry.gname or entry.mtime != STAMP
                        or entry.linkname):
                    raise PackageError('Unexpected tar metadata')
                end = entry.offset_data + ((entry.size + 511) // 512) * 512
                if entry.isdir():
                    if entry.name not in expected_dirs or entry.name in seen_dirs or entry.mode != 0o755:
                        raise PackageError('Unexpected or duplicate tar directory')
                    seen_dirs.add(entry.name)
                    continue
                if not entry.isfile() or not entry.name.startswith(APP_ID + '/') or entry.mode != 0o644:
                    raise PackageError('Nonregular file or wrong tar root/mode')
                rel = entry.name[len(APP_ID) + 1:]
                if not safe_path(rel) or rel not in files or rel in seen_files:
                    raise PackageError('Unexpected, duplicate or unsafe tar path')
                seen_files.add(rel)
                total += entry.size
                if total > MAX_UNPACKED or entry.size != len(files[rel]):
                    raise PackageError('Unexpected tar file size')
                handle = tar.extractfile(entry)
                if handle is None or handle.read() != files[rel]:
                    raise PackageError('Tar contents differ from verified source')
        if seen_files != set(files) or seen_dirs != expected_dirs:
            raise PackageError('Incomplete tar archive')
        # tarfile stops at its first terminator. Reject a hidden second archive
        # or non-zero trailer, including concatenated gzip members.
        if len(raw) < end + 1024 or any(raw[end:]):
            raise PackageError('Invalid tar terminator or trailing payload')
    except (OSError, EOFError, tarfile.TarError) as exc:
        raise PackageError('Invalid tar.gz: ' + str(exc)) from exc


def manual_archive(files: dict[str, bytes]) -> bytes:
    if SIGNATURE in files:
        raise PackageError('Unsigned artifact must not contain a signature')
    data = tar_bytes(files)
    verify_tar(data, files)
    if data != tar_bytes(files):
        raise PackageError('Double packaging was not deterministic')
    return data


def write_new(path: pathlib.Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise PackageError('Output exists; refusing overwrite: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)


def stage(archive: pathlib.Path, sha256: str, destination: pathlib.Path) -> dict:
    files, manifest = source_files(archive, sha256)
    if destination.exists() or destination.is_symlink():
        raise PackageError('Staging destination exists; refusing overwrite')
    app = destination / APP_ID
    app.mkdir(parents=True, mode=0o755)
    for rel, body in sorted(files.items()):
        target = app / rel
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        write_new(target, body)
        target.chmod(0o644)
    return manifest


def read_signed_stage(app: pathlib.Path, originals: dict[str, bytes]) -> dict[str, bytes]:
    if app.name != APP_ID or app.is_symlink() or not app.is_dir():
        raise PackageError('Expected a real directory named ' + APP_ID)
    files = {}
    allowed_dirs = expected_directories(originals | {SIGNATURE: b''})
    total = 0
    for path in app.rglob('*'):
        if path.is_symlink():
            raise PackageError('Symlink in staged application')
        rel = path.relative_to(app).as_posix()
        if path.is_dir():
            if APP_ID + '/' + rel not in allowed_dirs:
                raise PackageError('Unexpected staged directory')
            continue
        if rel not in originals and rel != SIGNATURE:
            raise PackageError('Unexpected staged file')
        if len(files) >= MAX_FILES:
            raise PackageError('Too many staged files')
        body = read_regular(path, MAX_SIGNATURE if rel == SIGNATURE else MAX_UNPACKED)
        total += len(body)
        if total > MAX_UNPACKED:
            raise PackageError('Staged files exceed size limit')
        files[rel] = body
    if set(files) != set(originals) | {SIGNATURE}:
        raise PackageError('Stage must contain exactly the original files and signature.json')
    if any(files[path] != body for path, body in originals.items()):
        raise PackageError('Application changed after source ZIP validation')
    return files


def checked_signature(files: dict[str, bytes]) -> dict:
    try:
        signing = json.loads(files[SIGNATURE], object_pairs_hook=unique_object)
        if not isinstance(signing, dict) or set(signing) != {'hashes', 'certificate', 'signature'}:
            raise PackageError('Invalid signature.json structure')
        expected = {path: digest(body, 'sha512') for path, body in sorted(files.items()) if path != SIGNATURE}
        # NC35 generateHashes explicitly strips leading slashes.
        if signing['hashes'] != expected:
            raise PackageError('Signature hashes differ from exact staged payload')
        if not isinstance(signing['certificate'], str) or len(signing['certificate']) > 65536:
            raise PackageError('Invalid embedded certificate')
        decoded_signature(signing['signature'])
        return signing
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise PackageError('Invalid Nextcloud signature.json: ' + str(exc)) from exc


def decoded_signature(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > 16384:
        raise PackageError('Invalid base64 signature')
    try:
        signature = base64.b64decode(''.join(value.split()), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PackageError('Invalid base64 signature') from exc
    if not signature:
        raise PackageError('Empty signature')
    return signature


def run_checked(command: list[str], *, input_data: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(command, input=input_data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PackageError('Verification command unavailable or timed out') from exc
    if result.returncode:
        # Never echo process output: configured server diagnostics may contain
        # unrelated sensitive paths or connection details.
        raise PackageError('Verification command failed: ' + pathlib.Path(command[0]).name)
    return result.stdout


def verify_code_signature(signing: dict) -> None:
    """Verify NC35's exact RSA-PSS format. CA trust is checked by occ below."""
    with tempfile.TemporaryDirectory(prefix='otp-signature-check-') as temp:
        directory = pathlib.Path(temp)
        certificate = directory / 'certificate.pem'
        certificate.write_text(signing['certificate'], encoding='ascii')
        public_key = directory / 'public.pem'
        public_key.write_bytes(run_checked(['openssl', 'x509', '-in', str(certificate), '-pubkey', '-noout']))
        signature = directory / 'signature.bin'
        signature.write_bytes(decoded_signature(signing['signature']))
        # PHP json_encode (without flags) escapes '/' and ksort orders keys.
        payload = json.dumps(signing['hashes'], sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True).replace('/', '\\/').encode('ascii')
        run_checked(['openssl', 'dgst', '-sha1', '-verify', str(public_key),
                     '-signature', str(signature), '-sigopt', 'rsa_padding_mode:pss',
                     '-sigopt', 'rsa_pss_saltlen:0', '-sigopt', 'rsa_mgf1_md:sha512'], input_data=payload)


def signed_archive(archive: pathlib.Path, sha256: str, app: pathlib.Path,
                   occ: pathlib.Path, php: str = 'php') -> tuple[bytes, dict]:
    originals, manifest = source_files(archive, sha256)
    files = read_signed_stage(app, originals)
    signing = checked_signature(files)
    verify_code_signature(signing)
    if not occ.is_file():
        raise PackageError('A working Nextcloud occ is required for certificate trust verification')
    # integrity:check-app would otherwise report success for an unsigned app.
    # Requiring signature.json above prevents that skip path.
    run_checked([php, str(occ.resolve()), 'integrity:check-app', APP_ID, '--path', str(app.resolve())])
    if read_signed_stage(app, originals) != files:
        raise PackageError('Signed stage changed during Nextcloud verification')
    data = tar_bytes(files)
    verify_tar(data, files)
    if data != tar_bytes(files):
        raise PackageError('Signed packaging was not deterministic')
    return data, manifest


def verify_detached(archive: pathlib.Path, sha256: str, signature_file: pathlib.Path,
                    certificate_file: pathlib.Path) -> None:
    data = read_regular(archive, MAX_ARCHIVE)
    if not re.fullmatch(r'[0-9a-f]{64}', sha256) or digest(data) != sha256:
        raise PackageError('Archive SHA256 mismatch')
    signature = decoded_signature(read_regular(signature_file, 16384).decode('ascii'))
    certificate = read_regular(certificate_file, 65536)
    # This is intentionally only the archive signature check. Certificate CA,
    # CN, code signature and payload checking belong to signed_archive/occ.
    with tempfile.TemporaryDirectory(prefix='otp-archive-signature-') as temp:
        directory = pathlib.Path(temp)
        public_key = directory / 'public.pem'
        public_key.write_bytes(run_checked(['openssl', 'x509', '-pubkey', '-noout'], input_data=certificate))
        signature_path = directory / 'signature.bin'
        signature_path.write_bytes(signature)
        run_checked(['openssl', 'dgst', '-sha512', '-verify', str(public_key),
                     '-signature', str(signature_path)], input_data=data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('unsigned', 'stage', 'package'):
        p = sub.add_parser(command)
        p.add_argument('--zip', type=pathlib.Path, required=True)
        p.add_argument('--sha256', required=True, help='Independently verified source ZIP SHA256')
        p.add_argument('--output', type=pathlib.Path, required=True)
        if command == 'package':
            p.add_argument('--signed-app-dir', type=pathlib.Path, required=True)
            p.add_argument('--occ', type=pathlib.Path, required=True, help='Working Nextcloud 35 occ')
            p.add_argument('--php', default='php')
    p = sub.add_parser('verify-detached')
    p.add_argument('--archive', type=pathlib.Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--signature', type=pathlib.Path, required=True, help='Base64 detached SHA512 signature file')
    p.add_argument('--certificate', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'stage':
            manifest = stage(args.zip, args.sha256, args.output)
            print('SIGNING_STAGE_PASS version=' + manifest['version'] + ' app=' + str(args.output / APP_ID))
        elif args.command == 'verify-detached':
            verify_detached(args.archive, args.sha256, args.signature, args.certificate)
            print('DETACHED_CRYPTOGRAPHIC_SIGNATURE_PASS certificate_trust=not_checked appstore_published=false')
        else:
            if args.command == 'unsigned':
                files, manifest = source_files(args.zip, args.sha256)
                data = manual_archive(files)
                status = 'UNSIGNED_TAR_PASS'
            else:
                if args.output.resolve().is_relative_to(args.signed_app_dir.resolve()):
                    raise PackageError('Output must be outside the signed app directory')
                data, manifest = signed_archive(args.zip, args.sha256, args.signed_app_dir, args.occ, args.php)
                status = 'NEXTCLOUD_CODE_SIGNED_TAR_PASS'
            write_new(args.output, data)
            print(status + ' version=' + manifest['version'] + ' sha256=' + digest(data)
                  + ' appstore_published=false archive=' + str(args.output))
            if args.command == 'package':
                print('Detached tar.gz signature and App Store registration/publication are still required.')
    except (PackageError, OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(2, 'PACKAGE_STOP: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
