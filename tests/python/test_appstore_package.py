"""Synthetic tests for the Nextcloud App Store staging and tar.gz packaging gate."""
from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
import appstore_package as appstore


class AppStorePackageTests(unittest.TestCase):
    def fixture(self, root: pathlib.Path, *, bugs: bool = True):
        xml = ('<info><id>passwords_otp</id><version>1.0.1</version>'
               '<category>security</category>'
               + ('<bugs>https://github.com/example/issues</bugs>' if bugs else '')
               + '</info>').encode()
        files = {
            'appinfo/info.xml': xml,
            'appinfo/routes.php': b'<?php // synthetic fixture',
            'js/app-101.js': b'/* synthetic compiled output */',
            'css/app-101.css': b'/* synthetic style */',
            'LICENSE': b'Synthetic licence notice',
        }
        manifest = {
            'app': 'passwords_otp', 'version': '1.0.1',
            'source_commit': 'a' * 40, 'production_approved': False,
            'files': {k: appstore.digest(v) for k, v in files.items()},
        }
        files['BUILD.json'] = (json.dumps(manifest, sort_keys=True) + '\n').encode()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr('passwords_otp/' + name, data)
        archive = root / 'synthetic.zip'
        archive.write_bytes(buf.getvalue())
        return archive, appstore.digest(buf.getvalue()), files

    @staticmethod
    def sign_synthetically(app: pathlib.Path, files: dict[str, bytes]):
        # Models only the documented Nextcloud signature.json shape/hash inventory.
        # Not a real Nextcloud certificate or cryptographic signature.
        signature = {
            'hashes': {'/' + k: appstore.digest(v, 'sha512') for k, v in files.items()},
            'certificate': '-----BEGIN CERTIFICATE-----\nSYNTHETIC ONLY\n-----END CERTIFICATE-----',
            'signature': 'SYNTHETIC-NOT-A-CRYPTOSIGNATURE',
        }
        (app / 'appinfo/signature.json').write_text(json.dumps(signature))

    def test_stage_and_deterministic_signed_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            archive, sha, files = self.fixture(root)
            manifest = appstore.stage(archive, sha, root / 'staged')
            self.assertEqual(manifest['version'], '1.0.1')
            app = root / 'staged/passwords_otp'
            self.assertEqual((app / 'js/app-101.js').read_bytes(), files['js/app-101.js'])
            with self.assertRaisesRegex(appstore.PackageError, 'already exists'):
                appstore.stage(archive, sha, root / 'staged')
            with self.assertRaisesRegex(appstore.PackageError, 'signature.json'):
                appstore.package(archive, sha, app, root / 'unsigned.tar.gz')
            self.assertFalse((root / 'unsigned.tar.gz').exists())
            self.sign_synthetically(app, files)
            digest1, _ = appstore.package(archive, sha, app, root / 'first.tar.gz')
            digest2, _ = appstore.package(archive, sha, app, root / 'second.tar.gz')
            self.assertEqual(digest1, digest2)
            self.assertEqual((root / 'first.tar.gz').read_bytes(), (root / 'second.tar.gz').read_bytes())
            appstore.verify_tar((root / 'first.tar.gz').read_bytes(),
                                {**files, 'appinfo/signature.json': (app / 'appinfo/signature.json').read_bytes()})
            with self.assertRaisesRegex(appstore.PackageError, 'refusing overwrite'):
                appstore.package(archive, sha, app, root / 'first.tar.gz')

    def test_wrong_zip_digest_and_missing_bugs_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            archive, sha, _ = self.fixture(root)
            with self.assertRaisesRegex(appstore.PackageError, 'SHA256 mismatch'):
                appstore.stage(archive, '0' * 64, root / 'bad')
            archive, sha, _ = self.fixture(root, bugs=False)
            with self.assertRaisesRegex(appstore.PackageError, 'bugs metadata'):
                appstore.stage(archive, sha, root / 'bad')

    def test_changed_file_extra_file_and_symlink_rejected(self):
        for violation in ('changed', 'extra', 'symlink'):
            with self.subTest(violation=violation), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                archive, sha, files = self.fixture(root)
                appstore.stage(archive, sha, root / 'staged')
                app = root / 'staged/passwords_otp'
                self.sign_synthetically(app, files)
                if violation == 'changed':
                    (app / 'js/app-101.js').write_text('unexpected content')
                elif violation == 'extra':
                    (app / 'node_modules').mkdir()
                    (app / 'node_modules/dependency.js').write_text('unexpected')
                else:
                    (app / 'js/surprise').symlink_to(app / 'LICENSE')
                with self.assertRaises(appstore.PackageError):
                    appstore.package(archive, sha, app, root / 'bad.tar.gz')

    def test_bad_signing_hashes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            archive, sha, files = self.fixture(root)
            appstore.stage(archive, sha, root / 'staged')
            app = root / 'staged/passwords_otp'
            self.sign_synthetically(app, files)
            sigpath = app / 'appinfo/signature.json'
            signature = json.loads(sigpath.read_text())
            signature['hashes']['/LICENSE'] = '0' * 128
            sigpath.write_text(json.dumps(signature))
            with self.assertRaisesRegex(appstore.PackageError, 'hashes do not match'):
                appstore.package(archive, sha, app, root / 'bad.tar.gz')

    def test_zip_traversal_and_wrong_top_level_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for bad in ('another_app/file.txt', 'passwords_otp/../escape'):
                with self.subTest(bad=bad):
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, 'w') as z:
                        z.writestr(bad, 'x')
                    archive = root / 'bad.zip'
                    archive.write_bytes(buf.getvalue())
                    with self.assertRaises(appstore.PackageError):
                        appstore.stage(archive, appstore.digest(buf.getvalue()), root / 'stage')


if __name__ == '__main__':
    unittest.main()
