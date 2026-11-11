#!/usr/bin/env python3
"""Single-instance, offline-capable development gates for the known localhost NC35 fixture.

Build never changes Nextcloud; preflight only inspects it; install requires an
exact per-commit build and preflight receipt, then uses transactional rollback.
These gates do NOT assert PostgreSQL/AIO or production compatibility.
"""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess, sys
from release import VERSION, digest, canonical_json, validate_package
ROOT=pathlib.Path(__file__).resolve().parents[1]
class GateError(RuntimeError):pass

def execute(args,*,env=None):
 print('RUN:',args[0],args[1]if len(args)>1 else '',flush=True)
 subprocess.run([str(item)for item in args],cwd=ROOT,env=env,check=True)

def source_commit():
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
  raise GateError('Source checkout is dirty; no unreviewed changes permitted')
 return commit

def candidate(commit):return ROOT/'.build'/commit

def receipt(path,data):
 if path.exists():raise GateError('Receipt already exists; never overwrite previous evidence: '+str(path))
 path.write_bytes(canonical_json(data));path.chmod(0o600)

def build(commit):
 directory=candidate(commit)
 if directory.exists():raise GateError('Build directory already exists; preserve and move it before a deliberate retry: '+str(directory))
 directory.mkdir(parents=True)
 node_major=int(subprocess.check_output(['node','-p','process.versions.node.split(".")[0]'],text=True))
 if node_major<22:raise GateError('Node.js 22 or newer required')
 execute(['npm','ci','--no-audit','--no-fund'])
 execute(['npm','test']);execute(['npm','run','test:client'])
 execute(['npm','audit','--audit-level=high'])
 execute([sys.executable,'-m','unittest','discover','-s','tests/python','-v'])
 execute(['npm','run','build']);execute(['node','--check','js/app-101.js'])
 first={path.name:path.read_bytes()for path in (ROOT/'js').glob('app-101.js*')}
 execute(['npm','run','build'])
 second={path.name:path.read_bytes()for path in (ROOT/'js').glob('app-101.js*')}
 if first!=second:raise GateError('Browser double build is not byte-identical')
 execute([sys.executable,'scripts/release.py',str(directory/'package')])
 archive=directory/'package'/f'passwords_otp-{VERSION}.zip';sha=digest(archive.read_bytes())
 _,manifest=validate_package(archive.read_bytes(),sha)
 if manifest['source_commit']!=commit or source_commit()!=commit:raise GateError('Source changed during build')
 receipt(directory/'build-pass.json',{'status':'PASS','source_commit':commit,
   'archive_sha256':sha,'version':VERSION,'production':False})
 print('BUILD_PASS:',archive,flush=True)

def load_build(commit):
 directory=candidate(commit);path=directory/'build-pass.json'
 if not path.is_file():raise GateError('No successful build receipt for this exact commit')
 record=json.loads(path.read_text());archive=directory/'package'/f'passwords_otp-{VERSION}.zip'
 if record.get('status')!='PASS' or record.get('production') is not False or record.get('source_commit')!=commit:
  raise GateError('Invalid build receipt')
 _,manifest=validate_package(archive.read_bytes(),record['archive_sha256'])
 if manifest['source_commit']!=commit:raise GateError('Package and source differ')
 return directory,archive,record

def inspect_fixture(backend):
 """Read-only inspection; deliberately requires the existing named local fixture."""
 before=backend.preflight()
 php=backend.exec('php','-r','echo PHP_VERSION;')
 db=backend.occ('config:system:get','dbtype')
 if not php.startswith('8.5.'):raise GateError('Expected the existing PHP 8.5 fixture, got '+php)
 if db!='mysql':raise GateError('Expected the existing MariaDB-backed fixture (Nextcloud dbtype=mysql), got '+db)
 if not str(before['passwords']).startswith('2026.11.'):
  raise GateError('Original Passwords version changed: inspect compatibility before continuing')
 backend.verify(before['version'],before['files'],before)
 return before,php,db

def fixture_digest(before,php,db):
 return digest(canonical_json({'fixture':before,'php_version':php,'dbtype':db}))

def preflight(commit):
 """No network downloads, no app writes, no new compose project."""
 from deploy import DockerBackend
 directory,archive,build_record=load_build(commit)
 output=directory/'localhost-preflight.json'
 if output.exists():raise GateError('Preflight receipt exists; preserve it and do not silently overwrite')
 backend=DockerBackend();before,php,db=inspect_fixture(backend)
 # The php:8.5-cli image was already present in the operator's last run;
 # --pull never prevents accidental hotel-network downloads.
 execute(['docker','run','--pull','never','--rm','--network','none','--read-only',
  '-v',str(ROOT)+':/src:ro','-w','/src','php:8.5-cli',
  'sh','-ec','find appinfo lib templates tests/php -name "*.php" -print0 | xargs -0 -n1 php -l >/dev/null; php tests/php/security.php'])
 venv=ROOT/'.build/desktop-venv/bin/python'
 if not venv.is_file():raise GateError('Existing offline Playwright venv missing; do not download images automatically')
 chrome=os.environ.get('CHROME_BIN') or shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('brave') or shutil.which('brave-browser')
 if not chrome:raise GateError('Desktop Chromium/Chrome/Brave not found')
 execute([str(venv),'tests/browser/desktop.py','--output',str(directory/'desktop')],env=dict(os.environ,CHROME_BIN=chrome))
 if source_commit()!=commit:raise GateError('Source changed during preflight')
 # Fail if any part of the live fixture changed while tests ran.
 newer,p2,d2=inspect_fixture(backend)
 if fixture_digest(before,php,db)!=fixture_digest(newer,p2,d2):
  raise GateError('Local Nextcloud fixture changed during preflight')
 receipt(output,{**build_record,'gate':'localhost-nc35-existing-instance',
  'nextcloud':before['nextcloud'],'passwords':before['passwords'],
  'php_version':php,'dbtype':db,'fixture_sha256':fixture_digest(before,php,db),
  'php_contract':'PASS','desktop':'PASS','matrix_cases':0,'aio_postgresql_covered':False})
 print('LOCALHOST_PREFLIGHT_PASS: local NC35 + installed Passwords + MariaDB; no app mutation',flush=True)
 print('NOT AIO/POSTGRESQL/PRODUCTION APPROVAL',flush=True)

def checked_fixture(commit):
 from deploy import DockerBackend
 directory,archive,build_record=load_build(commit)
 path=directory/'localhost-preflight.json'
 if not path.is_file():raise GateError('No successful localhost preflight receipt; do not bypass it')
 approved=json.loads(path.read_text())
 if any(approved.get(k)!=build_record.get(k) for k in ('status','source_commit','archive_sha256','version')) \
   or approved.get('gate')!='localhost-nc35-existing-instance' \
   or approved.get('production') is not False or approved.get('aio_postgresql_covered') is not False \
   or approved.get('php_contract')!='PASS' or approved.get('desktop')!='PASS' or approved.get('matrix_cases')!=0:
  raise GateError('Local preflight receipt does not match candidate')
 backend=DockerBackend();before,php,db=inspect_fixture(backend)
 if approved.get('fixture_sha256')!=fixture_digest(before,php,db) \
   or approved.get('nextcloud')!=before['nextcloud'] or approved.get('passwords')!=before['passwords'] \
   or approved.get('php_version')!=php or approved.get('dbtype')!=db:
  raise GateError('Local fixture has changed since preflight; refuse installation')
 if source_commit()!=commit:raise GateError('Source changed since build')
 return directory,archive,build_record,backend,before

def install(commit):
 _,archive,record,_,_=checked_fixture(commit)
 print('LOCALHOST_ONLY: replacing OTP app after verified backup; original Passwords untouched',flush=True)
 execute([sys.executable,'scripts/deploy.py',str(archive),
          '--sha256',record['archive_sha256'],'--localhost-test-only'])

def verify(commit):
 """Post-install read-only integrity check; not a substitute for a browser login."""
 from deploy import DockerBackend
 _,archive,record=load_build(commit)
 files,_=validate_package(archive.read_bytes(),record['archive_sha256'])
 backend=DockerBackend();before,_,_=inspect_fixture(backend)
 if before['version']!=VERSION:raise GateError('Candidate is not installed')
 hashes={name:digest(content)for name,content in files.items()}
 if before['files']!=hashes:raise GateError('Installed OTP files differ from the package')
 print('LOCALHOST_VERIFY_PASS: exact candidate files and HTTP assets; manual login/CSE still required',flush=True)

def main():
 parser=argparse.ArgumentParser()
 group=parser.add_mutually_exclusive_group(required=True)
 for mode in ('build','preflight','install','verify'):
  group.add_argument('--'+mode,action='store_true')
 args=parser.parse_args();os.umask(0o077);commit=source_commit()
 if args.build:build(commit)
 elif args.preflight:preflight(commit)
 elif args.install:install(commit)
 else:verify(commit)
if __name__=='__main__':
 try:main()
 except (RuntimeError,subprocess.SubprocessError,OSError,ValueError)as error:
  print('STOP: gate failed; no success receipt issued. '+str(error),file=sys.stderr);sys.exit(1)
