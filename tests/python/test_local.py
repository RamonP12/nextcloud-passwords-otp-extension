import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
import local
COMMIT='a'*40
BUILD={'status':'PASS','source_commit':COMMIT,'version':'1.0.1','archive_sha256':'b'*64,'production':False}
class FakeBackend:
 def __init__(self):
  self.before={'version':'0.6.1','files':{'appinfo/info.xml':'a'},'passwords':'2026.11.20','nextcloud':'35.0.2','container_id':'local-test'}
  self.php='8.5.12';self.db='mysql';self.verified=0
 def preflight(self):return dict(self.before)
 def exec(self,*args):return self.php
 def occ(self,*args):return self.db
 def verify(self,*args):self.verified+=1
class LocalGateTests(unittest.TestCase):
 def test_expected_fixture_inspected_read_only(self):
  b=FakeBackend();before,php,db=local.inspect_fixture(b)
  self.assertEqual((php,db,b.verified),('8.5.12','mysql',1));self.assertEqual(before['passwords'],'2026.11.20')
 def test_incompatible_versions_fail_closed(self):
  for attr,value in [('php','8.4.27'),('db','pgsql')]:
   with self.subTest(attr=attr):
    b=FakeBackend();setattr(b,attr,value)
    with self.assertRaises(local.GateError):local.inspect_fixture(b)
  b=FakeBackend();b.before['passwords']='2026.10.0'
  with self.assertRaises(local.GateError):local.inspect_fixture(b)
 def context(self,base):
  root=pathlib.Path(base);dir=root/'.build'/COMMIT;dir.mkdir(parents=True)
  python=root/'.build'/'desktop-venv'/'bin'/'python';python.parent.mkdir(parents=True);python.write_text('fixture')
  archive=dir/'package.zip';archive.write_bytes(b'fixture')
  return root,dir,archive,FakeBackend()
 def test_preflight_stays_offline_and_creates_commit_bound_receipt(self):
  with tempfile.TemporaryDirectory()as temp:
   root,dir,archive,backend=self.context(temp)
   with patch.object(local,'ROOT',root),patch.object(local,'load_build',return_value=(dir,archive,BUILD)),\
    patch.object(local,'source_commit',return_value=COMMIT),patch('deploy.DockerBackend',return_value=backend),\
    patch.object(local,'execute')as exec_cmd,patch.object(local.shutil,'which',return_value='/usr/bin/chromium'):
    local.preflight(COMMIT)
   rec=json.loads((dir/'localhost-preflight.json').read_text())
   self.assertEqual(rec['gate'],'localhost-nc35-existing-instance')
   self.assertEqual(rec['matrix_cases'],0);self.assertEqual(rec['desktop'],'PASS')
   self.assertIs(rec['aio_postgresql_covered'],False);self.assertEqual(backend.verified,2)
   commands=[c.args[0]for c in exec_cmd.call_args_list]
   self.assertEqual(len(commands),2);self.assertIn('--pull',commands[0]);self.assertIn('never',commands[0])
   self.assertTrue(any('desktop.py'in x for x in commands[1]))
   self.assertFalse(any('compose' in str(x) or 'pip' in str(x) for x in commands))
 def test_preflight_refuses_reuse_of_old_receipt(self):
  with tempfile.TemporaryDirectory()as temp:
   root,dir,archive,backend=self.context(temp);(dir/'localhost-preflight.json').write_text('{}')
   with patch.object(local,'ROOT',root),patch.object(local,'load_build',return_value=(dir,archive,BUILD)):
    with self.assertRaisesRegex(local.GateError,'exists'):local.preflight(COMMIT)
 def receipt(self,dir,backend):
  before,php,db=local.inspect_fixture(backend)
  d={**BUILD,'gate':'localhost-nc35-existing-instance','php_contract':'PASS','desktop':'PASS',
   'matrix_cases':0,'aio_postgresql_covered':False,'nextcloud':before['nextcloud'],'passwords':before['passwords'],
   'php_version':php,'dbtype':db,'fixture_sha256':local.fixture_digest(before,php,db)}
  (dir/'localhost-preflight.json').write_text(json.dumps(d));return d
 def test_install_requires_exact_unmodified_fixture(self):
  with tempfile.TemporaryDirectory()as temp:
   root,dir,archive,backend=self.context(temp);self.receipt(dir,backend)
   with patch.object(local,'ROOT',root),patch.object(local,'load_build',return_value=(dir,archive,BUILD)),\
    patch('deploy.DockerBackend',return_value=backend),patch.object(local,'source_commit',return_value=COMMIT),\
    patch.object(local,'execute')as execute:
    local.install(COMMIT);self.assertEqual(len(execute.call_args_list),1)
    cmd=execute.call_args_list[0].args[0]
    self.assertEqual(cmd[-1],'--localhost-test-only');self.assertIn('scripts/deploy.py',cmd)
 def test_install_refuses_changed_fixture_without_mutation(self):
  with tempfile.TemporaryDirectory()as temp:
   root,dir,archive,backend=self.context(temp);self.receipt(dir,backend)
   backend.before['files']={'appinfo/info.xml':'changed'}
   with patch.object(local,'ROOT',root),patch.object(local,'load_build',return_value=(dir,archive,BUILD)),\
    patch('deploy.DockerBackend',return_value=backend),patch.object(local,'execute')as execute:
    with self.assertRaisesRegex(local.GateError,'changed'):local.install(COMMIT)
    execute.assert_not_called()
 def test_install_refuses_incorrect_receipt(self):
  with tempfile.TemporaryDirectory()as temp:
   root,dir,archive,backend=self.context(temp);rec=self.receipt(dir,backend)
   rec['matrix_cases']=4;(dir/'localhost-preflight.json').write_text(json.dumps(rec))
   with patch.object(local,'ROOT',root),patch.object(local,'load_build',return_value=(dir,archive,BUILD)),\
    patch('deploy.DockerBackend',return_value=backend),patch.object(local,'execute')as execute:
    with self.assertRaisesRegex(local.GateError,'does not match'):local.install(COMMIT)
    execute.assert_not_called()
if __name__=='__main__':unittest.main()
