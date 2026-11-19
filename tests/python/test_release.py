"""Packaging and npm notice-boundary tests with synthetic fixtures only."""
import io
import json
import pathlib
import stat
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
import release


class PackageTests(unittest.TestCase):
    def fixture(self, root):
        for name in release.RUNTIME:
            if name == 'THIRD_PARTY_LICENSES.txt':
                continue
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')
        (root / 'appinfo/info.xml').write_text(
            '<info><id>passwords_otp</id><version>' + release.VERSION + '</version></info>')
        (root / 'LICENSE').write_text('GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007')
        (root / release.JS_ASSET).write_text(
            '/* synthetic packaging fixture; NOT an application */\nPASSWORDS_OTP_JS_111_VERIFIED\n' + 'x' * 10001)
        (root / release.CSS_ASSET).write_text('PASSWORDS_OTP_CSS_111_VERIFIED')
        packages = {
            '': {'version': release.VERSION, 'dependencies': {'passwords-client': '1.0.0-beta.6117', 'widget': '1.0.0'}},
            'node_modules/passwords-client': {'version': '1.0.0-beta.6117', 'license': 'ISC',
                'dependencies': {'process': '0.11.10', 'eventemitter3': '3.1.2', 'helper': '1.0.0'}},
            'node_modules/process': {'version': '0.11.10', 'license': 'MIT'},
            'node_modules/eventemitter3': {'version': '3.1.2', 'license': 'MIT'},
            'node_modules/widget': {'version': '1.0.0', 'license': 'Apache-2.0',
                'dependencies': {'helper': '2.0.0'}, 'peerDependencies': {'peer': '^1.0.0'}},
            'node_modules/widget/node_modules/helper': {'version': '2.0.0', 'license': 'BSD-2-Clause'},
            'node_modules/helper': {'version': '1.0.0', 'license': 'MIT'},
            'node_modules/peer': {'version': '1.0.0', 'license': 'MIT'},
            'node_modules/build-only': {'version': '1.0.0', 'license': 'MIT', 'dev': True},
        }
        for path, entry in packages.items():
            if path:
                entry['integrity'] = 'sha512-SYNTHETIC_TEST_FIXTURE_ONLY'
        lock = {'lockfileVersion': 3, 'packages': packages}
        (root / 'package-lock.json').write_bytes(release.canonical_json(lock))
        inventory = {'schema': 1, 'app_version': release.VERSION, 'packages': {}}
        for path, entry in release.runtime_packages(lock).items():
            name = release.dependency_name(path)
            directory = root / path
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'package.json').write_bytes(release.canonical_json({
                'name': name, 'version': entry['version'], 'license': entry['license'], 'author': 'Marius Wieschollek'}))
            record = {key: entry[key] for key in ('version', 'license', 'integrity')}
            record.update(name=name, notices=[])
            if name == 'passwords-client':
                record['notice_policy'] = 'reconstructed-passwords-client-isc'
            else:
                notice = ('SYNTHETIC NOTICE FOR UNIT TESTS, NOT FOR DISTRIBUTION.\n' * 3).encode()
                (directory / 'LICENSE').write_bytes(notice)
                record['notices'].append({'file': 'LICENSE', 'sha256': release.digest(notice)})
                if name == 'widget':
                    extra = ('SYNTHETIC SUPPLEMENTAL APACHE NOTICE.\n' * 4).encode()
                    (directory / 'NOTICE').write_bytes(extra)
                    record['notices'].append({'file': 'NOTICE', 'sha256': release.digest(extra)})
            inventory['packages'][path] = record
        (root / release.LICENSE_INVENTORY).parent.mkdir(parents=True, exist_ok=True)
        (root / release.LICENSE_INVENTORY).write_bytes(release.canonical_json(inventory))
        (root / 'node_modules/widget/index.js').write_text('/* synthetic source fixture */')
        (root / 'src').mkdir()
        (root / 'src/main.js').write_text('/* synthetic application fixture */')
        (root / 'vite.config.js').write_text('/* synthetic config fixture */')
        (root / 'package.json').write_text('{"version":"' + release.VERSION + '"}')
        metadata = {'schema': 2, 'mode': 'production', 'command': 'build',
            'assets': {name: release.digest((root / name).read_bytes()) for name in (release.JS_ASSET, release.CSS_ASSET)},
            'source_inputs': release.build_source_inputs(root),
            'modules': ['node_modules/widget/index.js'],
            'build_modules': ['src/main.js', 'node_modules/widget/index.js']}
        (root / release.BUNDLE_METADATA).parent.mkdir(parents=True, exist_ok=True)
        (root / release.BUNDLE_METADATA).write_bytes(release.canonical_json(metadata))
        return lock, inventory

    def test_deterministic_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, inventory = self.fixture(root)
            first, manifest = release.make_package(root, 'a' * 40)
            second, _ = release.make_package(root, 'a' * 40)
            self.assertEqual(first, second)
            files, verified = release.validate_package(first, release.digest(first))
            self.assertEqual(manifest, verified)
            self.assertTrue({'THIRD_PARTY_NOTICES.md', 'LICENSE', 'THIRD_PARTY_LICENSES.txt'} <= files.keys())
            notices = files['THIRD_PARTY_LICENSES.txt'].decode()
            for record in inventory['packages'].values():
                self.assertIn(f"{record['name']}@{record['version']} | {record['license']}", notices)
            self.assertIn('Reconstructed standard ISC notice', notices)
            self.assertIn('Original npm package file: NOTICE', notices)
            self.assertNotIn('build-only', notices)
            release.extract_checked(files, root / 'unpacked')
            self.assertEqual((root / 'unpacked' / release.JS_ASSET).read_bytes(), files[release.JS_ASSET])
            with self.assertRaises(release.PackageError):
                release.extract_checked(files, root / 'unpacked')

    def test_wrong_sha_and_missing_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            data, _ = release.make_package(root, 'a' * 40)
            with self.assertRaises(release.PackageError):
                release.validate_package(data, '0' * 64)
            (root / release.JS_ASSET).unlink()
            with self.assertRaises(release.PackageError):
                release.make_package(root, 'a' * 40)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            (root / 'img/app.svg').unlink()
            (root / 'img/app.svg').symlink_to(root / release.CSS_ASSET)
            with self.assertRaises(release.PackageError):
                release.make_package(root, 'a' * 40)

    def test_symlink_runtime_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            (root / 'img').rename(root / 'saved-img')
            (root / 'img').symlink_to(root / 'saved-img', target_is_directory=True)
            with self.assertRaisesRegex(release.PackageError, 'Symlink dependency file'):
                release.make_package(root, 'a' * 40)

    def test_removed_feature_marker_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            with (root / release.JS_ASSET).open('a') as handle:
                handle.write('hotpNext(')
            with self.assertRaises(release.PackageError):
                release.make_package(root, 'a' * 40)

    def test_zip_traversal_links_and_duplicate(self):
        for name, mode in [('../escape', stat.S_IFREG | 0o644),
                           ('passwords_otp/../escape', stat.S_IFREG | 0o644),
                           ('passwords_otp/' + release.JS_ASSET, stat.S_IFLNK | 0o777),
                           ('/absolute', stat.S_IFREG | 0o644),
                           ('passwords_otp\\escape', stat.S_IFREG | 0o644)]:
            with self.subTest(name=name, mode=mode):
                data = io.BytesIO()
                with zipfile.ZipFile(data, 'w') as archive:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    archive.writestr(info, b'x')
                with self.assertRaises(release.PackageError):
                    release.validate_package(data.getvalue(), release.digest(data.getvalue()))

    def changed_archive(self, root, mutate):
        self.fixture(root)
        data, _ = release.make_package(root, 'a' * 40)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        mutate(files)
        return release.archive_bytes(files)

    def test_manifest_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            def mutate(files):
                manifest = json.loads(files['passwords_otp/BUILD.json'])
                manifest['production_approved'] = True
                files['passwords_otp/BUILD.json'] = json.dumps(manifest).encode()
            changed = self.changed_archive(pathlib.Path(temp), mutate)
            with self.assertRaises(release.PackageError):
                release.validate_package(changed, release.digest(changed))

    def test_per_file_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            changed = self.changed_archive(pathlib.Path(temp), lambda files: files.update({'passwords_otp/img/app.svg': b'changed'}))
            with self.assertRaises(release.PackageError):
                release.validate_package(changed, release.digest(changed))

    def test_missing_runtime_license_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            (root / 'node_modules/eventemitter3/LICENSE').unlink()
            with self.assertRaisesRegex(release.PackageError, 'Missing dependency file'):
                release.make_package(root, 'a' * 40)

    def test_changed_dependency_metadata_fails_closed(self):
        for key, value in [('version', '1.0.0-beta.9999'), ('license', 'MIT'), ('integrity', 'sha512-OTHER')]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                lock, _ = self.fixture(root)
                lock['packages']['node_modules/passwords-client'][key] = value
                (root / 'package-lock.json').write_bytes(release.canonical_json(lock))
                with self.assertRaisesRegex(release.PackageError, 'Changed runtime dependency license/version/integrity'):
                    release.make_package(root, 'a' * 40)

    def test_unreviewed_runtime_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            lock, _ = self.fixture(root)
            lock['packages']['']['dependencies']['unknown-runtime-dep'] = '1.0.0'
            lock['packages']['node_modules/unknown-runtime-dep'] = {'version': '1.0.0', 'license': 'MIT'}
            (root / 'package-lock.json').write_bytes(release.canonical_json(lock))
            with self.assertRaisesRegex(release.PackageError, 'Unreviewed runtime dependency'):
                release.make_package(root, 'a' * 40)

    def test_symlink_notice_and_symlink_parent_fail_closed(self):
        for target in ('node_modules/process/LICENSE', 'node_modules/process'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                self.fixture(root)
                original = root / target
                moved = original.with_name(original.name + '.saved')
                original.rename(moved)
                original.symlink_to(moved, target_is_directory=moved.is_dir())
                with self.assertRaisesRegex(release.PackageError, 'Symlink dependency file'):
                    release.make_package(root, 'a' * 40)

    def test_original_license_notice_hash_catches_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            (root / 'node_modules/widget/NOTICE').write_text('incomplete')
            with self.assertRaisesRegex(release.PackageError, 'Original license notice changed/incomplete'):
                release.make_package(root, 'a' * 40)

    def test_license_notice_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            changed = self.changed_archive(pathlib.Path(temp), lambda files: files.update({
                'passwords_otp/THIRD_PARTY_LICENSES.txt': b'License names without license rights'}))
            with self.assertRaises(release.PackageError):
                release.validate_package(changed, release.digest(changed))

    def test_runtime_graph_keeps_nested_versions_and_peer_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            lock, _ = self.fixture(pathlib.Path(temp))
            found = release.runtime_packages(lock)
            self.assertEqual(found['node_modules/helper']['version'], '1.0.0')
            self.assertEqual(found['node_modules/widget/node_modules/helper']['version'], '2.0.0')
            self.assertIn('node_modules/peer', found)
            self.assertNotIn('node_modules/build-only', found)
            found['node_modules/peer']['dev'] = True
            self.assertIn('node_modules/peer', release.runtime_packages(lock), 'dev flag cannot hide required dependency')

    def test_required_peer_missing_fails_and_absent_optional_peer_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            lock, _ = self.fixture(pathlib.Path(temp))
            del lock['packages']['node_modules/peer']
            with self.assertRaisesRegex(release.PackageError, 'Missing locked runtime dependency'):
                release.runtime_packages(lock)
            lock['packages']['node_modules/widget']['peerDependenciesMeta'] = {'peer': {'optional': True}}
            self.assertNotIn('node_modules/peer', release.runtime_packages(lock))

    def test_bundle_metadata_rejects_changed_js_or_css(self):
        for asset in (release.JS_ASSET, release.CSS_ASSET):
            with self.subTest(asset=asset), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                self.fixture(root)
                with (root / asset).open('a') as handle:
                    handle.write('/* modified after build */')
                with self.assertRaisesRegex(release.PackageError, 'does not match emitted assets'):
                    release.make_package(root, 'a' * 40)

    def test_bundle_metadata_rejects_unreviewed_nested_optional_peer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            metadata = json.loads((root / release.BUNDLE_METADATA).read_text())
            metadata['modules'] = ['node_modules/widget/node_modules/unknown-peer/index.js']
            metadata['build_modules'] = ['src/main.js', *metadata['modules']]
            unknown = root / metadata['modules'][0]
            unknown.parent.mkdir(parents=True)
            unknown.write_text('/* synthetic unknown input */')
            (root / release.BUNDLE_METADATA).write_bytes(release.canonical_json(metadata))
            with self.assertRaisesRegex(release.PackageError, 'Unreviewed package in browser bundle'):
                release.make_package(root, 'a' * 40)

    def test_matching_asset_pair_is_rejected_after_source_or_config_edit(self):
        for source in ('src/main.js', 'vite.config.js', 'package.json'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                self.fixture(root)
                with (root / source).open('a') as handle:
                    handle.write('\n/* changed after compilation */')
                with self.assertRaisesRegex(release.PackageError, 'changed after compilation'):
                    release.make_package(root, 'a' * 40)

    def test_frontend_source_set_changes_invalidate_old_build(self):
        for operation in ('add', 'remove'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                self.fixture(root)
                if operation == 'add':
                    (root / 'src/new.js').write_text('/* newly introduced module */')
                else:
                    (root / 'src/main.js').unlink()
                with self.assertRaises(release.PackageError):
                    release.make_package(root, 'a' * 40)

    def test_dev_only_lock_change_still_requires_new_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            lock, _ = self.fixture(root)
            lock['packages']['node_modules/build-only']['version'] = '2.0.0'
            (root / 'package-lock.json').write_bytes(release.canonical_json(lock))
            with self.assertRaisesRegex(release.PackageError, 'changed after compilation'):
                release.make_package(root, 'a' * 40)

    def test_browser_fixture_module_cannot_enter_production_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            file = root / release.BUNDLE_METADATA
            metadata = json.loads(file.read_text())
            metadata['build_modules'].append('tests/browser/fixture-client.js')
            file.write_bytes(release.canonical_json(metadata))
            with self.assertRaisesRegex(release.PackageError, 'Unapproved source/fixture'):
                release.make_package(root, 'a' * 40)

    def test_dependency_module_cannot_be_omitted_from_license_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.fixture(root)
            file = root / release.BUNDLE_METADATA
            metadata = json.loads(file.read_text())
            metadata['build_modules'].append('node_modules/hidden-dependency/index.js')
            file.write_bytes(release.canonical_json(metadata))
            with self.assertRaisesRegex(release.PackageError, 'module inventory is incomplete'):
                release.make_package(root, 'a' * 40)

    def test_development_or_serve_output_cannot_be_packaged(self):
        for key, value in [('mode', 'development'), ('command', 'serve'), ('schema', 1)]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                self.fixture(root)
                file = root / release.BUNDLE_METADATA
                metadata = json.loads(file.read_text())
                metadata[key] = value
                file.write_bytes(release.canonical_json(metadata))
                with self.assertRaises(release.PackageError):
                    release.make_package(root, 'a' * 40)

    def test_release_cli_rechecks_commit_and_clean_tree_before_writing(self):
        for head, status in [('b' * 40, ''), ('a' * 40, ' M src/main.js\n')]:
            with self.subTest(head=head, status=status), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                output = root / 'candidate'
                with patch.object(release, 'ROOT', root), \
                        patch.object(sys, 'argv', ['release.py', str(output)]), \
                        patch.object(release, 'make_package', return_value=(b'identical archive fixture', {})), \
                        patch.object(release.subprocess, 'check_output', side_effect=['a' * 40, '', head, status]):
                    with self.assertRaisesRegex(release.PackageError, 'changed during packaging'):
                        release.main()
                self.assertFalse(output.exists(), 'no candidate output may survive a provenance mismatch')

    def test_unbundled_only_license_policy_cannot_reach_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, inventory = self.fixture(root)
            record = inventory['packages']['node_modules/widget']
            record.update(notices=[], notice_policy='unbundled-only', review_note='Synthetic missing notice test.')
            (root / release.LICENSE_INVENTORY).write_bytes(release.canonical_json(inventory))
            with self.assertRaisesRegex(release.PackageError, 'lacks reviewed original notice'):
                release.make_package(root, 'a' * 40)

    def test_source_notice_requires_immutable_url_and_unchanged_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, inventory = self.fixture(root)
            source = root / 'licenses/npm/widget-LICENSE'
            source.parent.mkdir(parents=True)
            source.write_bytes((root / 'node_modules/widget/LICENSE').read_bytes())
            record = {'source_file': 'licenses/npm/widget-LICENSE', 'sha256': release.digest(source.read_bytes()),
                'url': 'https://raw.githubusercontent.com/example/widget/' + 'a' * 40 + '/LICENSE'}
            inventory['packages']['node_modules/widget']['notices'] = [record]
            inventory_file = root / release.LICENSE_INVENTORY
            inventory_file.write_bytes(release.canonical_json(inventory))
            self.assertIn(b'Original upstream file:', release.third_party_license_bundle(root))
            record['url'] = 'https://raw.githubusercontent.com/example/widget/main/LICENSE'
            inventory_file.write_bytes(release.canonical_json(inventory))
            with self.assertRaisesRegex(release.PackageError, 'immutable source URL'):
                release.third_party_license_bundle(root)


if __name__ == '__main__':
    unittest.main()
