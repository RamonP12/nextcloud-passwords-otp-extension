import copy,json,pathlib,shutil,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
import deploy
from unittest.mock import patch
class Backend:
 def __init__(self,old,fail=None,restore_fail=False):
  self.old=old;self.files=deploy.file_hashes(old);self.enabled=True;self.version='0.6.1';self.calls=[];self.fail=fail;self.restore_fail=restore_fail;self.saved=None
 def step(self,name):
  self.calls.append(name)
  if self.fail==name:raise deploy.DeploymentError('injected '+name)
 def preflight(self):self.step('preflight');return {'version':self.version,'installed_version':self.version,'enabled':'yes','files':self.files,'passwords':'2026.11.20'}
 def prepare(self,tx,source,expected):self.step('prepare');self.target=expected
 def backup(self,destination):self.step('backup');shutil.copytree(self.old,destination)
 def disable(self):self.enabled=False;self.step('disable')
 def swap(self,tx):self.saved=self.files;self.files=self.target;self.step('swap')
 def activate(self,version,enabled):self.version=version;self.enabled=True;self.step('activate')
 def restart(self):self.step('restart')
 def verify(self,version,files,before):
  self.step('verify')
  if self.files!=files or self.version!=version or not self.enabled:raise deploy.DeploymentError('inconsistent state')
 def restore(self,tx,before):
  self.calls.append('restore')
  if self.restore_fail:raise deploy.DeploymentError('injected recovery failure')
  self.files=before['files'];self.version=before['version'];self.enabled=True;self.fail=None
 def cleanup_stage(self,tx):self.calls.append('cleanup')
class DeployTests(unittest.TestCase):
 def context(self,temp,fail=None,restore_fail=False):
  root=pathlib.Path(temp);old=root/'old';old.mkdir();(old/'file').write_text('old');new=root/'new';new.mkdir();(new/'file').write_text('new')
  return Backend(old,fail,restore_fail),new,root/'backups'
 def test_success(self):
  with tempfile.TemporaryDirectory()as temp:
   backend,new,backups=self.context(temp);backup=deploy.transaction(backend,new,'0.7.0',deploy.file_hashes(new),backups)
   self.assertEqual(backend.version,'0.7.0');self.assertEqual(json.loads((backup/'transaction.json').read_text())['phase'],'installed')
   self.assertEqual((backup/'passwords_otp/file').read_text(),'old');self.assertNotIn('restore',backend.calls)
 def test_each_failure_before_mutation_does_not_disable(self):
  for step in ['preflight','prepare','backup']:
   with self.subTest(step=step),tempfile.TemporaryDirectory()as temp:
    b,n,r=self.context(temp,step)
    with self.assertRaises(deploy.DeploymentError):deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
    self.assertTrue(b.enabled);self.assertEqual(b.version,'0.6.1');self.assertNotIn('disable',b.calls)
 def test_each_failure_after_disable_rolls_back_but_does_not_succeed(self):
  for step in ['disable','swap','activate','restart','verify']:
   with self.subTest(step=step),tempfile.TemporaryDirectory()as temp:
    b,n,r=self.context(temp,step)
    with self.assertRaises(deploy.RolledBack):deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
    self.assertTrue(b.enabled);self.assertEqual(b.version,'0.6.1');self.assertIn('restore',b.calls)
    state=json.loads(next(r.glob('*/transaction.json')).read_text());self.assertEqual(state['phase'],'rolled-back')
 def test_rollback_failure_preserves_evidence(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp,'swap',True)
   with self.assertRaisesRegex(deploy.DeploymentError,'automatic rollback failed'):deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
   state=json.loads(next(r.glob('*/transaction.json')).read_text());self.assertEqual(state['phase'],'recovery-failed')
   self.assertTrue(next(r.glob('*/passwords_otp/file')).is_file())
 def test_bad_backup_rejected_before_disable(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);b.backup=lambda dst:(dst.mkdir(),(dst/'file').write_text('corrupt'))
   with self.assertRaisesRegex(deploy.DeploymentError,'Backup verification'):deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
   self.assertNotIn('disable',b.calls)
 def test_explicit_rollback_of_completed_installation(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);backup=deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
   deploy.rollback_successful(b,backup)
   self.assertEqual(b.version,'0.6.1');self.assertEqual(json.loads((backup/'transaction.json').read_text())['phase'],'restored-manually')
 def test_explicit_rollback_refuses_changed_candidate(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);backup=deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
   b.files={'file':'changed'}
   with self.assertRaisesRegex(deploy.DeploymentError,'differs'):deploy.rollback_successful(b,backup)
   self.assertNotIn('restore',b.calls)
 def test_explicit_rollback_refuses_changed_backup(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);backup=deploy.transaction(b,n,'0.7.0',deploy.file_hashes(n),r)
   (backup/'passwords_otp/file').write_text('changed')
   with self.assertRaisesRegex(deploy.DeploymentError,'integrity'):deploy.rollback_successful(b,backup)
   self.assertNotIn('restore',b.calls)
 def test_remote_context_cannot_be_disguised_by_local_host_override(self):
  backend=deploy.DockerBackend()
  with patch.dict(deploy.os.environ,{'DOCKER_CONTEXT':'remote','DOCKER_HOST':'unix:///var/run/docker.sock'}):
   with patch.object(backend,'run',return_value=json.dumps([{'Endpoints':{'docker':{'Host':'ssh://remote'}}}])):
    with self.assertRaisesRegex(deploy.DeploymentError,'local Unix'):backend.preflight()
 def test_transaction_path_cannot_escape(self):
  for bad in ['../','x','a'*31,'a'*32+'/../x']:
   with self.assertRaises(deploy.DeploymentError):deploy.DockerBackend.paths(bad)
 def test_mount_mapping_requires_same_real_shared_path(self):
  a={'Mounts':[{'Type':'bind','Source':'/test/nc','Destination':'/var/www/html'}]}
  b={'Mounts':[{'Type':'bind','Source':'/test/nc/custom_apps','Destination':'/var/www/html/custom_apps'}]}
  self.assertEqual(deploy.DockerBackend.mount_location(a,deploy.LIVE),deploy.DockerBackend.mount_location(b,deploy.LIVE))
  with self.assertRaises(deploy.DeploymentError):deploy.DockerBackend.mount_location({'Mounts':[]},deploy.LIVE)
 def test_asset_mapping_supports_upgrade_and_rollback_from_070(self):
  self.assertEqual(deploy.asset_for_version('0.6.1'),'ap061')
  self.assertEqual(deploy.asset_for_version('0.7.0'),'app-070')
  self.assertEqual(deploy.asset_for_version('0.7.2'),'app-072')
  self.assertEqual(deploy.asset_for_version('0.7.1'),'app-071')
   self.assertEqual(deploy.asset_for_version('1.0.0'),'app-100')
  with self.assertRaises(deploy.DeploymentError):deploy.asset_for_version('0.7.99')
 def test_071_upgrade_and_explicit_rollback_to_070(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);b.version='0.7.0'
   backup=deploy.transaction(b,n,'0.7.1',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.1')
   deploy.rollback_successful(b,backup)
   self.assertEqual(b.version,'0.7.0')
 def test_failed_071_upgrade_restores_070(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp,'activate');b.version='0.7.0'
   with self.assertRaises(deploy.RolledBack):deploy.transaction(b,n,'0.7.1',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.0');self.assertTrue(b.enabled)

 def test_072_upgrade_and_explicit_rollback_to_071(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp);b.version='0.7.1'
   backup=deploy.transaction(b,n,'0.7.2',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.2')
   deploy.rollback_successful(b,backup)
   self.assertEqual(b.version,'0.7.1')
 def test_failed_072_upgrade_restores_071(self):
  with tempfile.TemporaryDirectory()as temp:
   b,n,r=self.context(temp,'activate');b.version='0.7.1'
   with self.assertRaises(deploy.RolledBack):deploy.transaction(b,n,'0.7.2',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.1');self.assertTrue(b.enabled)

 def test_073_upgrade_and_rollback_to_072(self):
  with tempfile.TemporaryDirectory() as temp:
   b,n,r=self.context(temp);b.version='0.7.2'
   backup=deploy.transaction(b,n,'0.7.3',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.3')
   deploy.rollback_successful(b,backup)
   self.assertEqual(b.version,'0.7.2')
 def test_failed_073_upgrade_restores_072(self):
  with tempfile.TemporaryDirectory() as temp:
   b,n,r=self.context(temp,'activate');b.version='0.7.2'
   with self.assertRaises(deploy.RolledBack):deploy.transaction(b,n,'0.7.3',deploy.file_hashes(n),r)
   self.assertEqual(b.version,'0.7.2');self.assertTrue(b.enabled)

if __name__=='__main__':unittest.main()
