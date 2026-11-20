import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = name => readFileSync(path.join(ROOT, name), 'utf8');
const exists = name => existsSync(path.join(ROOT, name));

test('current release metadata and historical acceptance are distinguished in public docs', () => {
    const readme = read('README.md'), info = read('appinfo/info.xml');
    const version = JSON.parse(read('package.json')).version;
    assert.equal(version, '1.1.3');
    assert.ok(readme.includes(`Latest published release: ${version}`));
    assert.ok(readme.includes('docs/VALIDATION_' + version + '.md'));
    assert.ok(readme.includes('/releases/tag/v' + version + ')'));
    assert.doesNotMatch(readme, /\*\*Latest published release: 1\.1\.3 \(unreleased\)/);
    assert.match(readme, /published \*\*v1\.0\.0\*\*/);
    for (const marker of ['docs/INSTALLATION.md', 'docs/COMPATIBILITY.md', 'docs/NEXTCLOUD_VUE_MIGRATION.md', 'THIRD_PARTY_NOTICES.md', '.github/SECURITY.md']) {
        assert.ok(readme.includes(marker), marker);
    }
    assert.ok(info.includes(`<version>${version}</version>`));
    assert.ok(read('scripts/release.py').includes(`VERSION='${version}'`));
    assert.ok(exists('LICENSE'));
    assert.match(read('CHANGELOG.md'), /\[1\.1\.3\].*2026-11-19/);
    assert.match(read('CHANGELOG.md'), /\[1\.1\.2\].*2026-11-19/);
});

test('published AIO commands retain SHA, group and matching-version boundaries', () => {
    const install = read('docs/AIO_MANUAL_INSTALL.md'), summary = read('docs/INSTALLATION.md');
    for (const marker of ['passwords_otp-1.1.3.zip', 'passwords_otp-1.0.0.zip', "--group 'otp-pilot'", '--preflight', '--install', '--verify', '--rollback', '--accept-browser-token-risk']) {
        assert.ok(install.includes(marker), marker);
    }
    assert.match(install, /first.time|first.install|first install/i);
    assert.match(summary, /including 0\.7\.3/);
    assert.match(summary, /1\.1\.3 scripts reject a 1\.0\.0 archive/);
    assert.match(install, /Use the corresponding source tag for\s+earlier archives/);
    assert.match(install, /No production upgrade path is introduced/);
});

test('public documentation keeps historical evidence and current local verification separate', () => {
    const retired = ['docs/STATUS.md', 'docs/AIO_READINESS.md', 'docs/BRANCH_CLEANUP.md', 'docs/CLEANUP.md', 'docs/OPERATIONS.md', 'docs/TEST_REPORT_070.md', 'docs/TEST_REPORT_071.md', 'docs/TEST_REPORT_072.md', 'docs/TEST_REPORT_073.md', 'docs/RELEASE_NOTES_073.md'];
    for (const name of retired) assert.equal(exists(name), false, name);
    for (const name of ['docs/USER_GUIDE.md', 'docs/SECURITY_REVIEW.md', 'docs/VALIDATION.md', 'docs/DEVELOPMENT.md']) {
        assert.equal(exists(name), true, name);
    }
    const development = read('docs/DEVELOPMENT.md');
    for (const command of ['npm ci', 'npm test', 'npm run test:client', 'npm run test:php', 'unittest discover', 'npm run build', 'tests/browser/desktop.py']) {
        assert.ok(development.includes(command), command);
    }
    assert.match(development, /historical v1\.0\.0 record/);
    assert.match(development, /clean committed checkout|clean, committed|clean committed source|clean committed/i);
});

test('GitHub Actions has only an explicit future manual trigger while quota is unavailable', () => {
    const workflow = read('.github/workflows/ci.yml');
    assert.match(workflow, /^  workflow_dispatch:/m);
    assert.doesNotMatch(workflow, /^  (push|pull_request|pull_request_target|schedule):/m);
    assert.match(workflow, /quota is exhausted/);
    const desktop = workflow.split('  desktop:')[1].split('  candidate:')[0];
    assert.ok(desktop.indexOf('npm ci') < desktop.indexOf('npm run build'));
    assert.ok(desktop.indexOf('npm run build') < desktop.indexOf('tests/browser/desktop.py'));
    assert.match(read('scripts/release.py'), /public-source-baseline/);
    for (const name of ['CONTRIBUTING.md', 'CODE_OF_CONDUCT.md', '.github/SECURITY.md', '.github/dependabot.yml', '.github/ISSUE_TEMPLATE/bug_report.yml', '.github/ISSUE_TEMPLATE/feature_request.yml', '.github/pull_request_template.md']) {
        assert.equal(exists(name), true, name);
    }
});

test('public docs do not expose the operator pilot server identity', () => {
    const docs = ['README.md', 'docs/INSTALLATION.md', 'docs/AIO_MANUAL_INSTALL.md', 'docs/ARCHITECTURE.md', 'docs/COMPATIBILITY.md', 'docs/USER_GUIDE.md', 'docs/DEVELOPMENT.md', 'docs/VALIDATION.md', 'docs/VALIDATION_1.1.3.md', 'docs/SECURITY_REVIEW.md'];
    for (const name of docs) {
        assert.doesNotMatch(read(name), /ncservervivaffeld|vivakirche-frauenfeld|ChurchTools-\d+|10\.10\.30\.3/i, name);
    }
});
