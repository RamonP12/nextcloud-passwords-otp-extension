import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const read=name=>readFileSync(path.join(ROOT,name),'utf8');
const exists=name=>existsSync(path.join(ROOT,name));

test('1.0.1 source candidate and released 1.0.0 are distinguished',()=>{
  const readme=read('README.md'),info=read('appinfo/info.xml');
  for(const marker of ['Version: 1.0.1','docs/INSTALLATION.md','docs/COMPATIBILITY.md','THIRD_PARTY_NOTICES.md','.github/SECURITY.md']){
    assert.ok(readme.includes(marker),marker);
  }
  assert.match(info,/<version>1\.0\.1<\/version>/);
  assert.ok(exists('LICENSE'));
  assert.ok(exists('CHANGELOG.md'));
});

test('Nextcloud appinfo includes mandatory bugs URL exactly once in schema order',()=>{
  const info=read('appinfo/info.xml');
  const bugs='<bugs>https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues</bugs>';
  assert.equal(info.split(bugs).length-1,1,'mandatory bugs URL absent or duplicated');
  const category=info.indexOf('</category>'), bugsAt=info.indexOf('<bugs>'), bugsEnd=info.indexOf('</bugs>'), repository=info.indexOf('<repository>'), dependencies=info.indexOf('<dependencies>');
  assert.ok(category>=0 && bugsAt>category,'bugs must follow category');
  assert.ok(repository>bugsEnd && dependencies>repository,'bugs must precede repository and dependencies in Nextcloud XSD sequence');
  assert.match(info,/<version>1\.0\.1<\/version>/);
  // Source: https://raw.githubusercontent.com/nextcloud/appstore/master/nextcloudappstore/api/v1/release/info.xsd
});

test('1.0.1 candidate has separate validation, release notes and gate checklist',()=>{
  for(const p of ['docs/RELEASE_NOTES_v1.0.1.md','docs/RELEASE_CHECKLIST_v1.0.1.md','docs/LOCAL_ACCEPTANCE_v1.0.0_2026-11-11.md','docs/RELEASE_INTEGRITY_v1.0.0.md'])assert.ok(exists(p),p);
  assert.match(read('docs/RELEASE_NOTES_v1.0.1.md'),/UNRELEASED SOURCE CANDIDATE/);
  assert.match(read('docs/RELEASE_CHECKLIST_v1.0.1.md'),/AIO\/PostgreSQL/);
  assert.match(read('docs/VALIDATION.md'),/49\/49/);
});

test('public AIO first-install documentation is SHA and group scoped',()=>{
  const install=read('docs/AIO_MANUAL_INSTALL.md'),summary=read('docs/INSTALLATION.md');
  for(const marker of ['passwords_otp-1.0.0.zip','SHA256_FROM_THIS_PACKAGE',"--group 'otp-pilot'",'--preflight','--install','--verify','--rollback','--accept-browser-token-risk']){
    assert.ok(install.includes(marker),marker);
  }
  assert.match(install,/first.time|first.install|first install/i);
  assert.match(summary,/existing 0\.7\.3|including 0\.7\.3/);
  assert.match(summary,/does not provide|refuses|cannot be/i);
});

test('no obsolete public development reports remain',()=>{
  const retired=['docs/STATUS.md','docs/AIO_READINESS.md','docs/BRANCH_CLEANUP.md','docs/CLEANUP.md','docs/OPERATIONS.md','docs/TEST_REPORT_070.md','docs/TEST_REPORT_071.md','docs/TEST_REPORT_072.md','docs/TEST_REPORT_073.md','docs/RELEASE_NOTES_073.md'];
  for(const name of retired)assert.equal(exists(name),false,name);
  for(const name of ['docs/USER_GUIDE.md','docs/SECURITY_REVIEW.md','docs/VALIDATION.md','docs/DEVELOPMENT.md']){
    assert.equal(exists(name),true,name);
  }
});

test('public security, contribution and issue templates exist',()=>{
  for(const name of ['CONTRIBUTING.md','CODE_OF_CONDUCT.md','.github/SECURITY.md','.github/dependabot.yml','.github/ISSUE_TEMPLATE/bug_report.yml','.github/ISSUE_TEMPLATE/feature_request.yml','.github/pull_request_template.md']){
    assert.equal(exists(name),true,name);
  }
  assert.match(read('.github/workflows/ci.yml'),/branches: \[main\]/);
  assert.match(read('scripts/release.py'),/VERSION='1\.0\.1'/);
  assert.match(read('scripts/release.py'),/public-source-baseline/);
});

test('public docs do not expose the operator pilot server identity',()=>{
  const docs=['README.md','docs/INSTALLATION.md','docs/AIO_MANUAL_INSTALL.md','docs/ARCHITECTURE.md','docs/COMPATIBILITY.md','docs/USER_GUIDE.md','docs/DEVELOPMENT.md','docs/VALIDATION.md','docs/SECURITY_REVIEW.md'];
  for(const name of docs){
    assert.doesNotMatch(read(name),/ncservervivaffeld|vivakirche-frauenfeld|ChurchTools-\d+|10\.10\.30\.3/i,name);
  }
});
