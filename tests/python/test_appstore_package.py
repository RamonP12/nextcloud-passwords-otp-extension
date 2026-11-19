"""Adversarial TAR/signing tests; ephemeral certificates are never distributed."""
import base64
import gzip
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
import appstore_package as package
import release


def fixture_files():
    files = {path: b'SYNTHETIC PACKAGING TEST FIXTURE ONLY\n' for path in release.RUNTIME}
    files['appinfo/info.xml'] = (
        '<info><id>passwords_otp</id><version>' + release.VERSION + '</version></info>').encode()
    manifest = {'schema': 1, 'app': 'passwords_otp', 'version': release.VERSION,
                'channel': 'public-source-baseline', 'production_approved': False,
                'source_commit': 'a' * 40,
                'files': {path: release.digest(data) for path, data in sorted(files.items())}}
    files['BUILD.json'] = release.canonical_json(manifest)
    return files


def zip_fixture(directory):
    files = fixture_files()
    data = release.archive_bytes({'passwords_otp/' + path: body for path, body in files.items()})
    archive = directory / 'source.zip'
    archive.write_bytes(data)
    return archive, release.digest(data), files


def edited_tar(data, transform):
    entries = []
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
        for entry in source:
            body = source.extractfile(entry).read() if entry.isfile() else None
            entries.append((entry, body))
    entries = transform(entries)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as target:
        for entry, body in entries:
            target.addfile(entry, io.BytesIO(body) if body is not None else None)
    return gzip.compress(output.getvalue(), mtime=0)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.files = fixture_files()
        self.tar = package.manual_archive(self.files)

    def test_unsigned_roundtrip_one_root_exact_payload_and_reproducible(self):
        self.assertEqual(self.tar, package.manual_archive(dict(reversed(list(self.files.items())))))
        package.verify_tar(self.tar, self.files)
        with tarfile.open(fileobj=io.BytesIO(self.tar), mode='r:gz') as archive:
            self.assertEqual({entry.name.split('/')[0] for entry in archive}, {'passwords_otp'})
            names = archive.getnames()
            self.assertNotIn('passwords_otp/appinfo/signature.json', names)
            self.assertIn('passwords_otp/' + release.JS_ASSET, names)
            self.assertIn('passwords_otp/BUILD.json', names)

    def test_refuse_unknown_source_entry_even_with_updated_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            files = self.files | {'secret.key': b'NEVER A REAL KEY'}
            manifest = json.loads(files['BUILD.json'])
            manifest['files']['secret.key'] = release.digest(files['secret.key'])
            files['BUILD.json'] = release.canonical_json(manifest)
            data = release.archive_bytes({'passwords_otp/' + path: body for path, body in files.items()})
            archive = directory / 'bad.zip'
            archive.write_bytes(data)
            with self.assertRaises(package.PackageError):
                package.source_files(archive, release.digest(data))

    def test_reject_wrong_zip_digest_and_truncated_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, sha, _ = zip_fixture(pathlib.Path(temp))
            with self.assertRaises(package.PackageError):
                package.source_files(archive, '0' * 64)
            archive.write_bytes(b'not a ZIP')
            with self.assertRaises(package.PackageError):
                package.source_files(archive, package.digest(archive.read_bytes()))

    def test_no_archive_traversal_absolute_or_second_root(self):
        for name in ('passwords_otp/../../outside', '/absolute', 'other/appinfo/info.xml'):
            with self.subTest(name=name):
                def alter(entries):
                    for entry, _ in entries:
                        if entry.isfile():
                            entry.name = name
                            break
                    return entries
                with self.assertRaises(package.PackageError):
                    package.verify_tar(edited_tar(self.tar, alter), self.files)

    def test_reject_symlink_hardlink_fifo_and_device(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind):
                def alter(entries):
                    entry = tarfile.TarInfo('passwords_otp/rogue')
                    entry.type = kind
                    entry.mode = 0o644
                    if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                        entry.linkname = '/outside'
                    return entries + [(entry, None)]
                with self.assertRaises(package.PackageError):
                    package.verify_tar(edited_tar(self.tar, alter), self.files)

    def test_reject_duplicate_file_directory_and_missing_file(self):
        mutations = (
            lambda entries: entries + [next(pair for pair in entries if pair[0].isfile())],
            lambda entries: entries + [next(pair for pair in entries if pair[0].isdir())],
            lambda entries: entries[:-1],
        )
        for mutation in mutations:
            with self.assertRaises(package.PackageError):
                package.verify_tar(edited_tar(self.tar, mutation), self.files)

    def test_reject_modified_content(self):
        def alter(entries):
            for index, (entry, body) in enumerate(entries):
                if body:
                    entries[index] = (entry, bytes([body[0] ^ 1]) + body[1:])
                    break
            return entries
        with self.assertRaises(package.PackageError):
            package.verify_tar(edited_tar(self.tar, alter), self.files)

    def test_reject_hidden_payload_and_concatenated_gzip(self):
        for data in (gzip.compress(gzip.decompress(self.tar) + b'HIDDEN'),
                     self.tar + gzip.compress(b'HIDDEN')):
            with self.assertRaises(package.PackageError):
                package.verify_tar(data, self.files)

    def test_reject_owner_mode_and_excessive_size(self):
        for attribute, value in (('uid', 1000), ('mode', 0o777)):
            def alter(entries):
                setattr(entries[0][0], attribute, value)
                return entries
            with self.assertRaises(package.PackageError):
                package.verify_tar(edited_tar(self.tar, alter), self.files)
        with patch.object(package, 'MAX_UNPACKED', 1), self.assertRaises(package.PackageError):
            package.verify_tar(self.tar, self.files)

    def test_unsigned_artifact_never_accepts_signature(self):
        with self.assertRaises(package.PackageError):
            package.manual_archive(self.files | {package.SIGNATURE: b'{}'})

    def test_staging_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            archive, sha, files = zip_fixture(directory)
            destination = directory / 'stage'
            package.stage(archive, sha, destination)
            self.assertEqual((destination / package.APP_ID / release.JS_ASSET).read_bytes(), files[release.JS_ASSET])
            with self.assertRaises(package.PackageError):
                package.stage(archive, sha, destination)

    def test_missing_extra_changed_or_symlink_stage_rejected(self):
        for action in ('missing-signature', 'extra', 'changed', 'symlink', 'extra-directory'):
            with tempfile.TemporaryDirectory() as temp, self.subTest(action=action):
                directory = pathlib.Path(temp)
                archive, sha, files = zip_fixture(directory)
                package.stage(archive, sha, directory / 'stage')
                app = directory / 'stage' / package.APP_ID
                if action != 'missing-signature':
                    (app / package.SIGNATURE).write_text('{}')
                if action == 'extra':
                    (app / 'secrets.key').write_bytes(b'fixture')
                if action == 'changed':
                    (app / release.JS_ASSET).write_bytes(b'altered')
                if action == 'symlink':
                    (app / 'linked').symlink_to(app / release.JS_ASSET)
                if action == 'extra-directory':
                    (app / 'unexpected').mkdir()
                with self.assertRaises(package.PackageError):
                    package.read_signed_stage(app, files)


@unittest.skipUnless(shutil.which('openssl'), 'OpenSSL required for real cryptographic negative tests')
class SigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='otp-ephemeral-test-keys-')
        cls.directory = pathlib.Path(cls.temporary.name)
        cls.key = cls.directory / 'fixture.key'
        cls.certificate = cls.directory / 'fixture.crt'
        # This certificate is synthetic, untrusted and destroyed after tests.
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(cls.key), '-out', str(cls.certificate), '-days', '1',
                        '-subj', '/CN=passwords_otp'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def signed_files(self, files):
        hashes = {path: package.digest(body, 'sha512') for path, body in sorted(files.items())}
        payload = json.dumps(hashes, sort_keys=True, separators=(',', ':')).replace('/', '\\/').encode()
        signature = subprocess.run(['openssl', 'dgst', '-sha1', '-sign', str(self.key),
                                    '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:0',
                                    '-sigopt', 'rsa_mgf1_md:sha512'], input=payload,
                                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        signing = {'hashes': hashes, 'certificate': self.certificate.read_text(),
                   'signature': base64.b64encode(signature).decode()}
        return files | {package.SIGNATURE: json.dumps(signing).encode()}

    def test_real_nc35_format_relative_hash_keys_and_rsa_pss(self):
        files = self.signed_files(fixture_files())
        signing = package.checked_signature(files)
        package.verify_code_signature(signing)
        self.assertTrue(all(not path.startswith('/') for path in signing['hashes']))

    def test_reject_old_draft_slash_hashes(self):
        files = self.signed_files(fixture_files())
        signing = json.loads(files[package.SIGNATURE])
        signing['hashes'] = {'/' + path: value for path, value in signing['hashes'].items()}
        files[package.SIGNATURE] = json.dumps(signing).encode()
        with self.assertRaises(package.PackageError):
            package.checked_signature(files)

    def test_reject_forged_signature_even_when_hashes_match(self):
        files = self.signed_files(fixture_files())
        signing = package.checked_signature(files)
        signature = package.decoded_signature(signing['signature'])
        signing['signature'] = base64.b64encode(bytes([signature[0] ^ 1]) + signature[1:]).decode()
        with self.assertRaises(package.PackageError):
            package.verify_code_signature(signing)

    def test_reject_changed_payload_and_duplicate_json_keys(self):
        files = self.signed_files(fixture_files())
        files[release.JS_ASSET] += b'tampered'
        with self.assertRaises(package.PackageError):
            package.checked_signature(files)
        files = self.signed_files(fixture_files())
        files[package.SIGNATURE] = b'{"hashes":{},"hashes":{},"signature":"a","certificate":"x"}'
        with self.assertRaises(package.PackageError):
            package.checked_signature(files)

    def test_untrusted_signing_gate_cannot_emit_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            archive, sha, originals = zip_fixture(directory)
            package.stage(archive, sha, directory / 'stage')
            app = directory / 'stage' / package.APP_ID
            signed = self.signed_files(originals)
            (app / package.SIGNATURE).write_bytes(signed[package.SIGNATURE])
            # A working cryptographic signature alone is insufficient.
            with self.assertRaises(package.PackageError):
                package.signed_archive(archive, sha, app, directory / 'missing-occ')
            occ = directory / 'occ'
            occ.write_text('synthetic command path; never executed')
            original_runner = package.run_checked
            def reject_occ(command, **kwargs):
                if 'integrity:check-app' in command:
                    self.assertEqual(command[2:], ['integrity:check-app', package.APP_ID,
                                                  '--path', str(app.resolve())])
                    raise package.PackageError('Synthetic rejection of untrusted certificate')
                return original_runner(command, **kwargs)
            with patch.object(package, 'run_checked', side_effect=reject_occ), self.assertRaises(package.PackageError):
                package.signed_archive(archive, sha, app, occ)

    def test_race_after_occ_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            archive, sha, originals = zip_fixture(directory)
            package.stage(archive, sha, directory / 'stage')
            app = directory / 'stage' / package.APP_ID
            (app / package.SIGNATURE).write_bytes(self.signed_files(originals)[package.SIGNATURE])
            occ = directory / 'occ'
            occ.write_text('synthetic command path; never executed')
            original_runner = package.run_checked
            def tamper(command, **kwargs):
                if 'integrity:check-app' in command:
                    (app / release.JS_ASSET).write_bytes(b'changed during verification')
                    return b''
                return original_runner(command, **kwargs)
            with patch.object(package, 'run_checked', side_effect=tamper), self.assertRaises(package.PackageError):
                package.signed_archive(archive, sha, app, occ)

    def test_detached_sha512_signature_pass_and_tampered_archive_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            archive = directory / 'fixture.tar.gz'
            data = package.tar_bytes(self.signed_files(fixture_files()))
            archive.write_bytes(data)
            binary = subprocess.run(['openssl', 'dgst', '-sha512', '-sign', str(self.key)], input=data,
                                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            signature = directory / 'signature.base64'
            signature.write_bytes(base64.encodebytes(binary))
            package.verify_detached(archive, package.digest(data), signature, self.certificate)
            archive.write_bytes(data + b'tampered')
            with self.assertRaises(package.PackageError):
                package.verify_detached(archive, package.digest(archive.read_bytes()), signature, self.certificate)
            archive.write_bytes(data)
            signature.write_bytes(b'not-valid-base64!')
            with self.assertRaises(package.PackageError):
                package.verify_detached(archive, package.digest(data), signature, self.certificate)


if __name__ == '__main__':
    unittest.main()
