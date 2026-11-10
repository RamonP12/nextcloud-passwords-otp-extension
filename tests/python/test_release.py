import hashlib,importlib.util,io,json,pathlib,stat,tempfile,unittest,zipfile,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
import release
class PackageTests(unittest.TestCase):
 def fixture(self,root):
  for name in release.RUNTIME:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
  (root/'appinfo/info.xml').write_text('<info><id>passwords_otp</id><version>1.0.0</version></info>')
  (root/'LICENSE').write_text('GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007')
  (root/'js/app-100.js').write_text('/* synthetic packaging fixture; NOT an application */\nPASSWORDS_OTP_JS_100_VERIFIED\n'+'x'*10001)
  (root/'css/app-100.css').write_text('PASSWORDS_OTP_CSS_100_VERIFIED')
 def test_deterministic_roundtrip(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root);a,ma=release.make_package(root,'a'*40);b,mb=release.make_package(root,'a'*40)
   self.assertEqual(a,b);files,m=release.validate_package(a,release.digest(a));self.assertEqual(ma,m);self.assertIn('THIRD_PARTY_NOTICES.md',files);self.assertIn('LICENSE',files)
   release.extract_checked(files,root/'unpacked');self.assertEqual((root/'unpacked/js/app-100.js').read_bytes(),files['js/app-100.js'])
   with self.assertRaises(release.PackageError):release.extract_checked(files,root/'unpacked')
 def test_wrong_sha_and_missing_bundle(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root);a,_=release.make_package(root,'a'*40)
   with self.assertRaises(release.PackageError):release.validate_package(a,'0'*64)
   (root/'js/app-100.js').unlink()
   with self.assertRaises(release.PackageError):release.make_package(root,'a'*40)
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root);(root/'img/app.svg').unlink();(root/'img/app.svg').symlink_to(root/'css/app-100.css')
   with self.assertRaises(release.PackageError):release.make_package(root,'a'*40)
 def test_removed_feature_marker_rejected(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root)
   with(root/'js/app-100.js').open('a')as f:f.write('hotpNext(')
   with self.assertRaises(release.PackageError):release.make_package(root,'a'*40)
 def test_zip_traversal_links_and_duplicate(self):
  for name,mode in [('../escape',stat.S_IFREG|0o644),('passwords_otp/../escape',stat.S_IFREG|0o644),('passwords_otp/js/app-100.js',stat.S_IFLNK|0o777),('/absolute',stat.S_IFREG|0o644),('passwords_otp\\escape',stat.S_IFREG|0o644)]:
   with self.subTest(name=name,mode=mode):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w')as z:
     info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,b'x')
    with self.assertRaises(release.PackageError):release.validate_package(data.getvalue(),release.digest(data.getvalue()))
 def test_manifest_tampering_rejected(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root);data,_=release.make_package(root,'a'*40)
   z=zipfile.ZipFile(io.BytesIO(data));files={i:z.read(i)for i in z.namelist()};manifest=json.loads(files['passwords_otp/BUILD.json']);manifest['production_approved']=True
   files['passwords_otp/BUILD.json']=json.dumps(manifest).encode();changed=release.archive_bytes(files)
   with self.assertRaises(release.PackageError):release.validate_package(changed,release.digest(changed))
 def test_per_file_tampering_rejected(self):
  with tempfile.TemporaryDirectory()as temp:
   root=pathlib.Path(temp);self.fixture(root);data,_=release.make_package(root,'a'*40)
   z=zipfile.ZipFile(io.BytesIO(data));files={i:z.read(i)for i in z.namelist()};files['passwords_otp/img/app.svg']=b'changed'
   changed=release.archive_bytes(files)
   with self.assertRaises(release.PackageError):release.validate_package(changed,release.digest(changed))
if __name__=='__main__':unittest.main()
