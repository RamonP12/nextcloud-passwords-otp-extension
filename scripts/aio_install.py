#!/usr/bin/env python3
"""Deliberately restricted, first-install-only Nextcloud AIO sideloader.

No remote Docker engines, app-store downloads, Nextcloud upgrades, database
patches, maintenance-mode changes, container restarts or unrelated app writes.

Requires scripts/release.py beside this file to validate a prebuilt artifact.
The package is an unsigned PUBLIC SOURCE PILOT BUILD; the explicit acknowledgement is
not a substitute for operator security/backup approval or AIO compatibility.
"""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from release import VERSION, PackageError, digest, validate_package, extract_checked

CONTAINER = 'nextcloud-aio-nextcloud'
APP = 'passwords_otp'
CUSTOM = '/var/www/html/custom_apps'
LIVE = CUSTOM + '/' + APP
IMAGE = re.compile(r'^ghcr\.io/nextcloud-releases/aio-nextcloud(?::[^\s/]+|@sha256:[0-9a-f]{64})$')
EXPECTED_VERSION = '1.0.1'
DEFAULT_STATE = pathlib.Path('/var/lib/passwords-otp-aio-installer')
MAX_APP_FILE_BYTES = 30 * 1024 * 1024

class AioError(RuntimeError):
    pass


def short_error(command: list[str]) -> str:
    if command[:2] == ['docker', 'exec']:
        return 'docker exec (Nextcloud AIO)'
    return ' '.join(command[:2])


def invoke(command: list[str], *, timeout: int = 60, allow_failure: bool = False) -> str | None:
    try:
        result = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        if allow_failure:
            return None
        raise AioError('Command timeout/unavailable: ' + short_error(command)) from exc
    if result.returncode:
        if allow_failure:
            return None
        # Suppress arbitrary upstream responses: these may contain secrets.
        raise AioError('Command failed: ' + short_error(command))
    return result.stdout.strip()


def local_docker():
    context = os.environ.get('DOCKER_CONTEXT', '')
    if context and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', context):
        raise AioError('Invalid Docker context')
    raw = invoke(['docker', 'context', 'inspect', *([context] if context else [])])
    settings = json.loads(raw)
    if len(settings) != 1:
        raise AioError('Ambiguous Docker context')
    endpoint = (settings[0]['Endpoints']['docker']['Host'] if context else
                os.environ.get('DOCKER_HOST') or settings[0]['Endpoints']['docker']['Host'])
    if not endpoint.startswith('unix://'):
        raise AioError('Remote/non-Unix Docker endpoint forbidden')
    if os.environ.get('DOCKER_TLS_VERIFY'):
        raise AioError('Unexpected Docker TLS override')


class AioBackend:
    def docker(self, *args: str, allow_failure: bool = False, timeout: int = 60):
        return invoke(['docker', *args], timeout=timeout, allow_failure=allow_failure)

    def exec(self, *args: str, user: str = 'root', allow_failure: bool = False):
        return self.docker('exec', '-u', user, CONTAINER, *args, allow_failure=allow_failure)

    def occ(self, *args: str, allow_failure: bool = False):
        return self.exec('php', '/var/www/html/occ', *args, user='www-data', allow_failure=allow_failure)

    def sh(self, code: str, *args: str, user: str = 'root', allow_failure: bool = False):
        return self.exec('sh', '-ec', code, '--', *args, user=user, allow_failure=allow_failure)

    @staticmethod
    def source_mount(info: dict) -> dict:
        mounts = [m for m in info.get('Mounts', []) if
                  CUSTOM == m.get('Destination') or CUSTOM.startswith(m.get('Destination', '').rstrip('/') + '/')]
        if not mounts:
            raise AioError('No persistent mount for AIO custom_apps')
        m = max(mounts, key=lambda value: len(value['Destination']))
        if m.get('Type') not in ('volume', 'bind') or m.get('RW') is not True:
            raise AioError('custom_apps is not on a writable volume/bind mount')
        if not m.get('Source') or not os.path.isabs(m['Source']):
            raise AioError('Invalid AIO mount source')
        return {key: m.get(key) for key in ('Type', 'Name', 'Source', 'Destination', 'RW')}

    def check_base(self, expected_nc: str, expected_passwords: str) -> dict:
        local_docker()
        info = json.loads(self.docker('inspect', CONTAINER))[0]
        if info.get('Name') != '/' + CONTAINER or info.get('State', {}).get('Running') is not True:
            raise AioError('Expected running nextcloud-aio-nextcloud container')
        image = info.get('Config', {}).get('Image', '')
        if not IMAGE.fullmatch(image):
            raise AioError('Unexpected Docker image; refusing nonstandard AIO target')
        mount = self.source_mount(info)
        self.sh('test -d "$1" && test ! -L "$1" && test -w "$1"', CUSTOM, user='www-data')
        status = json.loads(self.occ('status', '--output=json'))
        version = str(status.get('versionstring', ''))
        if not (status.get('installed') is True and status.get('maintenance') is False
                and (version == expected_nc or version.startswith(expected_nc + '.'))):
            raise AioError('Nextcloud version/maintenance state differs from approved target')
        if self.occ('config:system:get', 'dbtype') != 'pgsql':
            raise AioError('Expected AIO/PostgreSQL; refusing non-AIO database')
        checker = self.occ('config:system:get', 'appcodechecker', allow_failure=True)
        if checker is not None and checker.strip().lower() in ('1', 'true', 'yes', 'on'):
            raise AioError('appcodechecker is enabled; private upstream APIs may be rejected')
        php = self.exec('php', '-r', 'echo PHP_VERSION;', user='www-data')
        found = re.match(r'^(\d+)\.(\d+)\.(\d+)', php)
        if not found or not (8, 3) <= tuple(int(x) for x in found.groups()[:2]) <= (8, 5):
            raise AioError('PHP version outside appinfo/info.xml compatibility range')
        apps = json.loads(self.occ('app:list', '--output=json'))
        enabled = apps.get('enabled', {})
        if enabled.get('passwords') != expected_passwords:
            raise AioError('Original Passwords version mismatch')
        # Document the upstream version separately, never modify its files.
        return {'container_id': info['Id'], 'image': image, 'mount': mount,
                'nextcloud': version, 'passwords': enabled['passwords'],
                'php': php, 'db': 'pgsql', 'checker': checker or '',
                'passwords_enabled': True}

    def check_absent(self) -> None:
        apps = json.loads(self.occ('app:list', '--output=json'))
        if APP in apps.get('enabled', {}) or APP in apps.get('disabled', {}):
            raise AioError('OTP app already registered; this installer handles first install only')
        if self.occ('config:app:get', APP, 'installed_version', allow_failure=True):
            raise AioError('Existing OTP app database metadata found; manual investigation required')
        self.sh('test ! -e "$1" && test ! -L "$1"', LIVE)

    def fingerprint(self, expected_nc: str, expected_passwords: str) -> dict:
        facts = self.check_base(expected_nc, expected_passwords)
        self.check_absent()
        return facts

    def hashes(self, path: str) -> dict[str, str]:
        script = r'''$r=$argv[1];if(is_link($r)||!is_dir($r))exit(2);$a=[];$n=0;$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($r,FilesystemIterator::SKIP_DOTS));foreach($it as $f){if($f->isLink())exit(3);if($f->isFile()){$p=substr($f->getPathname(),strlen($r)+1);if(!preg_match("~^[A-Za-z0-9_./-]+$~",$p))exit(4);$n+=$f->getSize();if($n>31457280)exit(5);$a[$p]=hash_file("sha256",$f->getPathname());}}ksort($a);echo json_encode($a,JSON_THROW_ON_ERROR);'''
        return json.loads(self.exec('php', '-r', script, '--', path))

    def prepare(self, package_dir: pathlib.Path, transaction: str, expected: dict[str, str]) -> str:
        stage_root = CUSTOM + '/.passwords-otp-stage-' + transaction
        stage = stage_root + '/' + APP
        self.sh('test ! -e "$1" && test ! -L "$1" && mkdir -m 0700 "$1"', stage_root)
        self.docker('cp', str(package_dir) + '/.', CONTAINER + ':' + stage, timeout=120)
        self.sh('chown -R 33:0 "$1" && find "$1" -type d -exec chmod 0755 {} + && find "$1" -type f -exec chmod 0644 {} +', stage)
        if self.hashes(stage) != expected:
            raise AioError('Staged package hash mismatch')
        return stage_root

    def publish(self, stage_root: str) -> None:
        stage = stage_root + '/' + APP
        self.sh('test -d "$1" && test ! -L "$1" && test ! -e "$2" && test ! -L "$2" && mv -- "$1" "$2"', stage, LIVE)

    def assert_group_exists(self, group: str) -> None:
        # Nextcloud 35 `app:enable --groups=...` ignores unknown IDs and may
        # silently enable for *everyone*. Check the exact group ID with the
        # supported OCC group:info command; never trust names or a zero exit
        # status from app:enable alone.
        try:
            data = json.loads(self.occ('group:info', group, '--output=json'))
        except (AioError, TypeError, ValueError) as exc:
            raise AioError('Target group does not exist or cannot be verified: ' + repr(group)) from exc
        if not isinstance(data, dict) or data.get('groupID') != group:
            raise AioError('Group ID mismatch; refusing to enable app for an unverified group')

    def assert_enabled_scope(self, group: str | None) -> None:
        raw = self.occ('config:app:get', APP, 'enabled')
        if group is None:
            if raw != 'yes':
                raise AioError('Expected explicit all-users scope; stored app scope differs')
            return
        try:
            groups = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise AioError('Enabled app group scope missing or invalid; refusing PASS') from exc
        if not isinstance(groups, list) or groups != [group]:
            # In particular raw='yes' is an unsafe all-users fallback.
            raise AioError('Enabled app scope differs from requested group; refusing PASS')

    def enable(self, group: str | None) -> None:
        # Recheck immediately before OCC in case the group was deleted after
        # the read-only preflight or during package staging.
        if group is not None:
            self.assert_group_exists(group)
            self.occ('app:enable', '--groups=' + group, APP)
        else:
            self.occ('app:enable', APP)
        # Verify immediately; a success exit code is NOT evidence of scope.
        self.assert_enabled_scope(group)

    def verify(self, version: str, expected: dict[str, str], before: dict, group: str | None) -> None:
        # Independently reverify scope for --verify and --rollback as well.
        self.assert_enabled_scope(group)
        facts = self.check_base(before['nextcloud'], before['passwords'])
        if facts != before:
            raise AioError('AIO environment changed since preflight/installation')
        if self.hashes(LIVE) != expected:
            raise AioError('Installed package hashes changed')
        apps = json.loads(self.occ('app:list', '--output=json'))
        if apps.get('enabled', {}).get(APP) != version:
            raise AioError('App not registered and enabled with expected version')
        if self.occ('config:app:get', APP, 'installed_version') != version:
            raise AioError('App database installed_version mismatch')
        path = self.occ('app:getpath', APP)
        if path.rstrip('/') != LIVE:
            raise AioError('Nextcloud registered wrong app path')
        # All-user and group-specific scopes were already checked above.

    def verify_emergency(self, version: str, expected: dict[str, str], before: dict) -> None:
        """Emergency disable after an AIO update. Verify app identity and
        persisted volume, not the obsolete container ID or server versions.
        This mode may only REMOVE access to the OTP app, never enable it.
        """
        local_docker()
        info = json.loads(self.docker('inspect', CONTAINER))[0]
        if info.get('Name') != '/' + CONTAINER or info.get('State', {}).get('Running') is not True:
            raise AioError('Emergency rollback target is not running Nextcloud AIO')
        if not IMAGE.fullmatch(info.get('Config', {}).get('Image', '')):
            raise AioError('Emergency rollback refuses unexpected container image')
        mount = self.source_mount(info)
        saved = before.get('mount')
        if not isinstance(saved, dict) or any(
                mount.get(key) != saved.get(key) for key in ('Type', 'Name', 'Source', 'Destination')):
            raise AioError('Persistent AIO app-volume identity changed; STOP')
        if self.occ('config:system:get', 'dbtype') != 'pgsql':
            raise AioError('Emergency rollback requires original AIO/PostgreSQL target')
        self.sh('test -d "$1" && test ! -L "$1"', LIVE)
        if self.hashes(LIVE) != expected:
            raise AioError('OTP app files changed; emergency rollback refuses unknown app')
        apps = json.loads(self.occ('app:list', '--output=json'))
        if apps.get('enabled', {}).get(APP) != version:
            raise AioError('Expected OTP app is not enabled with reviewed version')
        if self.occ('config:app:get', APP, 'installed_version') != version:
            raise AioError('OTP appconfig version changed; cannot verify original install')
        if self.occ('app:getpath', APP).rstrip('/') != LIVE:
            raise AioError('OTP app path changed; refusing emergency rollback')
        # Scope may have drifted (including accidental global activation);
        # do not require the old scope to disable an otherwise exact app.

    def live_exists(self) -> bool:
        return self.sh('test -d "$1" && test ! -L "$1"', LIVE, allow_failure=True) is not None

    def safe_disable(self) -> bool:
        self.occ('app:disable', APP, allow_failure=True)
        apps = json.loads(self.occ('app:list', '--output=json'))
        return APP not in apps.get('enabled', {})

    def move_out_of_service(self, transaction: str, label: str) -> str:
        # Never remove or overwrite unrelated app data. Preserve the exact installed files.
        dest = CUSTOM + '/.passwords-otp-' + label + '-' + transaction
        self.sh('test -d "$1" && test ! -L "$1" && test ! -e "$2" && test ! -L "$2" && mv -- "$1" "$2"', LIVE, dest)
        return dest

    def cleanup_stage(self, stage_root: str) -> None:
        # Stage root is generated by us and always inside fixed custom_apps.
        if not re.fullmatch(r'/var/www/html/custom_apps/\.passwords-otp-stage-[0-9a-f]{32}', stage_root):
            raise AioError('Unsafe stage cleanup path')
        self.sh('test ! -L "$1" && if test -d "$1"; then rm -rf -- "$1"; fi', stage_root)


def load_package(path: pathlib.Path, sha: str) -> tuple[dict[str, bytes], dict, dict[str, str]]:
    data = path.read_bytes()
    files, manifest = validate_package(data, sha)
    if manifest['version'] != EXPECTED_VERSION or manifest['production_approved'] is not False \
            or manifest['channel'] != 'public-source-baseline':
        raise AioError('Only the reviewed 1.0.1 public source pilot package is supported')
    return files, manifest, {name: digest(contents) for name, contents in files.items()}


def safe_write(path: pathlib.Path, data: dict) -> None:
    temp = path.with_name(path.name + '.new-' + uuid.uuid4().hex)
    with temp.open('x') as out:
        os.chmod(temp, 0o600)
        json.dump(data, out, sort_keys=True, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)


@contextmanager
def exclusive_state(state_dir: pathlib.Path):
    if state_dir.is_symlink():
        raise AioError('State directory must not be a symlink')
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    lock = state_dir / '.lock'
    with lock.open('a+') as handle:
        os.chmod(lock, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield state_dir


def requested_scope(args) -> dict:
    # Required for both preflight and install, not just the writing operation.
    if (args.group is not None) == bool(args.all_users):
        raise AioError('Specify exactly one of --group GROUP and --all-users')
    if args.group is None:
        return {'type': 'all-users', 'group': None}
    group = args.group
    if not group or len(group) > 100 or group != group.strip() or re.search(r'[\x00-\x1f\x7f]', group):
        raise AioError('Invalid group identifier')
    return {'type': 'group', 'group': group}


def snapshot(args, backend: AioBackend, manifest: dict, sha: str):
    scope = requested_scope(args)
    facts = backend.fingerprint(args.expect_nc, args.expect_passwords)
    if scope['type'] == 'group':
        backend.assert_group_exists(scope['group'])
    return {'schema': 1, 'app': APP, 'package_sha256': sha,
            'source_commit': manifest['source_commit'], 'version': manifest['version'],
            'expected_nc': args.expect_nc, 'expected_passwords': args.expect_passwords,
            'scope': scope, 'environment': facts}


def load_receipt(path: pathlib.Path, expected: dict) -> dict:
    if not path.is_file() or path.is_symlink():
        raise AioError('No valid prior preflight receipt')
    recorded = json.loads(path.read_text())
    if recorded != expected:
        raise AioError('Source, target or live AIO state changed since preflight')
    return recorded


def preflight(args, backend: AioBackend, manifest: dict, sha: str, state: pathlib.Path):
    record = snapshot(args, backend, manifest, sha)
    safe_write(state / 'preflight.json', record)
    scope = record['scope']
    print('AIO_PREFLIGHT_PASS: NC=' + record['environment']['nextcloud'] +
          ' Passwords=' + record['environment']['passwords'] +
          ' PHP=' + record['environment']['php'] + ' PostgreSQL (read-only)' +
          ' scope=' + (scope['group'] if scope['type'] == 'group' else 'ALL-USERS'))
    print('AIO_PILOT_GATE: unsigned public source pilot package, no app changes, no general production approval')


def require_confirmation(args):
    if not (args.confirm_production and args.ack_backup and args.accept_unapproved_rc
            and args.accept_browser_token_risk):
        raise AioError('Install requires explicit --confirm-production, --ack-aio-backup, '
                       '--accept-unapproved-rc and --accept-browser-token-risk')
    requested_scope(args)


def install(args, backend: AioBackend, files: dict[str, bytes],
            manifest: dict, expected: dict[str, str], state: pathlib.Path):
    require_confirmation(args)
    if (state / 'install.json').exists():
        raise AioError('An install receipt already exists; refuse repeated install')
    current = snapshot(args, backend, manifest, args.sha256)
    load_receipt(state / 'preflight.json', current)
    transaction = uuid.uuid4().hex
    journal = state / ('install-' + transaction + '.json')
    status = {'schema': 1, 'transaction': transaction, 'state': 'validated',
              'before': current, 'production_approved': False, 'group': args.group}
    safe_write(journal, status)
    stage_root = None
    publish_attempted = False
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix='otp-aio-') as scratch:
            source = pathlib.Path(scratch) / APP
            extract_checked(files, source)
            stage_root = backend.prepare(source, transaction, expected)
            status['state'] = 'stage-verified'; safe_write(journal, status)
            publish_attempted = True
            backend.publish(stage_root)
            published = True
            status['state'] = 'published'; safe_write(journal, status)
            backend.enable(args.group)
            status['state'] = 'enabled'; safe_write(journal, status)
            backend.verify(EXPECTED_VERSION, expected, current['environment'], args.group)
            status['state'] = 'verified'; safe_write(journal, status)
            safe_write(state / 'install.json', {'schema': 1, 'transaction': transaction,
                'sha256': args.sha256, 'version': EXPECTED_VERSION,
                'environment': current['environment'], 'group': args.group,
                'scope': current['scope'],
                'source_commit': manifest['source_commit'], 'state': 'installed'})
            print('AIO_INSTALL_PASS: ' + EXPECTED_VERSION + '; app registered using occ app:enable')
            print('AIO_JOURNAL: ' + str(journal))
    except BaseException as exc:
        if publish_attempted and not published:
            try:
                published = backend.live_exists()
            except Exception:
                status['state'] = 'publication-state-unknown'; safe_write(journal, status)
                raise AioError('Could not determine whether package was published; STOP') from exc
        if published:
            # Prior app was absent. Disable the newly introduced app and preserve
            # its files if possible; never touch the original Passwords app.
            try:
                if not backend.safe_disable():
                    raise AioError('Could not confirm OTP app disabled')
                preserved = backend.move_out_of_service(transaction, 'failed')
                status['state'] = 'failed-disabled-preserved'; status['preserved'] = preserved
                safe_write(journal, status)
                raise AioError('Install failed; new OTP app disabled, files preserved. '
                               'Review appconfig/AIO state before retry') from exc
            except AioError as recovery_error:
                if status['state'] == 'failed-disabled-preserved':
                    raise
                status['state'] = 'recovery-incomplete'; safe_write(journal, status)
                raise AioError('Install and recovery could not be verified; STOP and inspect AIO') from recovery_error
        status['state'] = 'aborted-before-publish'; safe_write(journal, status)
        raise
    finally:
        if stage_root:
            try: backend.cleanup_stage(stage_root)
            except AioError: print('WARNING: staging cleanup incomplete; inspect journal', file=sys.stderr)


def verify(args, backend: AioBackend, manifest: dict, expected: dict[str, str], state: pathlib.Path):
    receipt_path = state / 'install.json'
    if not receipt_path.is_file():
        raise AioError('No successful AIO install receipt')
    rec = json.loads(receipt_path.read_text())
    if (rec.get('state') != 'installed' or rec.get('sha256') != args.sha256
            or rec.get('source_commit') != manifest['source_commit']
            or rec.get('scope') != ({'type': 'group', 'group': rec.get('group')}
                                   if rec.get('group') is not None
                                   else {'type': 'all-users', 'group': None})):
        raise AioError('Install receipt does not match archive/scope')
    backend.verify(EXPECTED_VERSION, expected, rec['environment'], rec.get('group'))
    print('AIO_VERIFY_PASS: AIO app registration, version, files, original Passwords unchanged')
    print('BROWSER_LOGIN/CSE/COPY/SHARING still require operator acceptance')


def rollback(args, backend: AioBackend, manifest: dict,
             expected: dict[str, str], state: pathlib.Path):
    if not (args.confirm_production and args.ack_backup):
        raise AioError('Rollback requires --confirm-production --ack-aio-backup')
    receipt_path = state / 'install.json'
    if not receipt_path.is_file():
        raise AioError('No successful first-install receipt to roll back')
    rec = json.loads(receipt_path.read_text())
    if rec.get('state') != 'installed' or rec.get('sha256') != args.sha256 \
            or rec.get('source_commit') != manifest['source_commit'] \
            or rec.get('scope') != ({'type': 'group', 'group': rec.get('group')}
                                   if rec.get('group') is not None
                                   else {'type': 'all-users', 'group': None}):
        raise AioError('Rollback requires exact installed archive/commit/scope')
    emergency = bool(getattr(args, 'allow_aio_update_for_rollback', False))
    if emergency:
        # Explicit opt-in for UPDATED AIO containers; still verify the original
        # app files, package, database registration and persistent volume.
        backend.verify_emergency(EXPECTED_VERSION, expected, rec['environment'])
    else:
        backend.verify(EXPECTED_VERSION, expected, rec['environment'], rec.get('group'))
    if not backend.safe_disable():
        raise AioError('Refuse moving still-enabled app')
    preserved = backend.move_out_of_service(rec['transaction'], 'rollback')
    safe_write(receipt_path, {**rec, 'state': 'rolled-back', 'preserved': preserved,
                              'mode': 'emergency-after-aio-update' if emergency else 'strict'})
    print(('AIO_EMERGENCY_DISABLE_PASS' if emergency else 'AIO_ROLLBACK_PASS') +
          ': OTP app disabled, files preserved; original Passwords unaffected')
    print('NOTE: App DB metadata may remain; full AIO backup needed for database-level rollback')


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description='AIO first-install ONLY (requires prebuilt, SHA-verified OTP 1.0.1)')
    group = parser.add_mutually_exclusive_group(required=True)
    for mode in ('inspect', 'preflight', 'install', 'verify', 'rollback'):
        group.add_argument('--' + mode, action='store_true')
    parser.add_argument('--package', type=pathlib.Path)
    parser.add_argument('--sha256')
    parser.add_argument('--state-dir', type=pathlib.Path, default=DEFAULT_STATE)
    parser.add_argument('--expect-nc', default='35.0.2')
    parser.add_argument('--expect-passwords', default='2026.11.20')
    parser.add_argument('--confirm-production', action='store_true')
    parser.add_argument('--ack-aio-backup', dest='ack_backup', action='store_true')
    parser.add_argument('--accept-unapproved-rc', action='store_true')
    parser.add_argument('--accept-browser-token-risk', action='store_true')
    parser.add_argument('--group')
    parser.add_argument('--all-users', action='store_true')
    parser.add_argument('--allow-aio-update-for-rollback', action='store_true',
                        help='Emergency disable ONLY after AIO container/version updates; verifies same app files and volume')
    args = parser.parse_args(argv)
    if args.allow_aio_update_for_rollback and not args.rollback:
        parser.error('--allow-aio-update-for-rollback only permitted with --rollback')
    os.umask(0o077)
    backend = AioBackend()
    if args.inspect:
        base = backend.check_base(args.expect_nc, args.expect_passwords)
        print('AIO_INSPECT_PASS:', json.dumps({'nextcloud':base['nextcloud'],
            'passwords':base['passwords'],'php':base['php'],'db':base['db'],
            'image':base['image'],'mount':base['mount']['Destination']}, sort_keys=True))
        return
    if not args.package or not args.sha256 or not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Explicit --package and 64-character --sha256 required')
    files, manifest, expected = load_package(args.package.resolve(), args.sha256)
    with exclusive_state(args.state_dir.resolve()) as state:
        if args.preflight:
            preflight(args, backend, manifest, args.sha256, state)
        elif args.install:
            install(args, backend, files, manifest, expected, state)
        elif args.verify:
            verify(args, backend, manifest, expected, state)
        else:
            rollback(args, backend, manifest, expected, state)


if __name__ == '__main__':
    try:
        main()
    except (AioError, PackageError, ValueError, KeyError, OSError,
            json.JSONDecodeError) as e:
        print('STOP:', str(e) if isinstance(e, AioError) else type(e).__name__, file=sys.stderr)
        sys.exit(1)
