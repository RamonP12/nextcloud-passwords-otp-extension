#!/usr/bin/env python3
"""Strict deterministic development package. No installation or network access."""
from __future__ import annotations
import argparse, hashlib, io, json, os, pathlib, re, stat, subprocess, zipfile
import xml.etree.ElementTree as ET
VERSION='1.0.0'
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=('appinfo/info.xml','appinfo/routes.php','lib/AppInfo/Application.php',
 'lib/Controller/PageController.php','lib/Service/PasswordsAuthAdapter.php','templates/main.php',
 'css/app-100.css','js/app-100.js','img/app.svg','LICENSE','THIRD_PARTY_NOTICES.md')
OPTIONAL=('js/app-100.js.LEGAL.txt',)
MAX_ARCHIVE=20*1024*1024
MAX_UNPACKED=30*1024*1024
STAMP=(2026,1,1,0,0,0)
class PackageError(ValueError): pass

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def identity(xml:bytes)->tuple[str,str]:
    if b'<!DOCTYPE' in xml or len(xml)>100000:raise PackageError('Unsafe metadata')
    node=ET.fromstring(xml)
    return node.findtext('id',''),node.findtext('version','')

def canonical_json(value)->bytes:return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode()

def archive_bytes(files:dict[str,bytes])->bytes:
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for path,body in sorted(files.items()):
            if not safe_relative(path):raise PackageError('Unsafe archive path')
            item=zipfile.ZipInfo(path,date_time=STAMP);item.create_system=3
            item.external_attr=(stat.S_IFREG|0o644)<<16;item.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(item,body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return buffer.getvalue()

def safe_relative(path:str)->bool:
    return bool(path) and '\\' not in path and '\x00' not in path and not path.startswith('/') and all(part not in ('','..','.') for part in path.split('/'))

def make_package(root:pathlib.Path,commit:str)->tuple[bytes,dict]:
    if not re.fullmatch(r'[0-9a-f]{40}',commit):raise PackageError('Invalid source commit')
    files={}
    for relative in RUNTIME+OPTIONAL:
        path=root/relative
        if relative in OPTIONAL and not path.exists():continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):raise PackageError('Unsafe/missing runtime input: '+relative)
        files[relative]=path.read_bytes()
    if identity(files['appinfo/info.xml'])!=('passwords_otp',VERSION):raise PackageError('Unexpected app identity/version')
    js=files['js/app-100.js']
    if len(js)<10000 or b'PASSWORDS_OTP_JS_100_VERIFIED' not in js:raise PackageError('Fresh production bundle missing')
    if b'PASSWORDS_OTP_CSS_100_VERIFIED' not in files['css/app-100.css']:raise PackageError('CSS marker missing')
    for prohibited in [b'OTP_HOTP_WRITE_TEST_ONLY',b'hotpNext(',b'hotp-commit-uncertain',b'passwords-otp-ap4__']:
        if prohibited in js:raise PackageError('Removed feature leaked into runtime')
    manifest={'schema':1,'app':'passwords_otp','version':VERSION,'source_commit':commit,'channel':'public-source-baseline',
        'production_approved':False,'files':{key:digest(value) for key,value in sorted(files.items())}}
    files['BUILD.json']=canonical_json(manifest)
    data=archive_bytes({'passwords_otp/'+key:value for key,value in files.items()})
    validate_package(data,digest(data))
    return data,manifest

def validate_package(data:bytes,expected_sha256:str)->tuple[dict[str,bytes],dict]:
    if not re.fullmatch(r'[0-9a-f]{64}',expected_sha256) or digest(data)!=expected_sha256:raise PackageError('Archive SHA256 mismatch')
    if not data or len(data)>MAX_ARCHIVE:raise PackageError('Archive size limit')
    files={};total=0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if len(z.infolist())>len(RUNTIME)+len(OPTIONAL)+1:raise PackageError('Unexpected file count')
        for item in z.infolist():
            if not safe_relative(item.filename) or not item.filename.startswith('passwords_otp/'):raise PackageError('Unsafe archive entry')
            path=item.filename.removeprefix('passwords_otp/')
            if path not in (*RUNTIME,*OPTIONAL,'BUILD.json') or path in files:raise PackageError('Unexpected/duplicate entry')
            mode=item.external_attr>>16
            if item.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG)) or item.flag_bits&1:raise PackageError('Nonregular/encrypted entry')
            total+=item.file_size
            if total>MAX_UNPACKED or item.file_size>MAX_UNPACKED:raise PackageError('Unpacked size limit')
            files[path]=z.read(item)
    if set(RUNTIME)-set(files) or 'BUILD.json' not in files:raise PackageError('Incomplete package')
    manifest=json.loads(files['BUILD.json'])
    if manifest.get('schema')!=1 or manifest.get('app')!='passwords_otp' or manifest.get('version')!=VERSION or manifest.get('production_approved') is not False:
        raise PackageError('Incorrect manifest identity/channel')
    if manifest.get('channel')!='public-source-baseline' or not re.fullmatch(r'[0-9a-f]{40}',manifest.get('source_commit','')):raise PackageError('Invalid provenance')
    expected={key:digest(value) for key,value in sorted(files.items()) if key!='BUILD.json'}
    if expected!=manifest.get('files') or identity(files['appinfo/info.xml'])!=('passwords_otp',VERSION):raise PackageError('Manifest file integrity mismatch')
    return files,manifest

def extract_checked(files:dict[str,bytes],destination:pathlib.Path)->None:
    if destination.exists():raise PackageError('Extraction destination already exists')
    destination.mkdir(parents=True,mode=0o700)
    for relative,body in files.items():
        if relative not in (*RUNTIME,*OPTIONAL,'BUILD.json'):raise PackageError('Unknown extraction input')
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with target.open('xb') as handle:handle.write(body)
        target.chmod(0o600)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=pathlib.Path);args=parser.parse_args()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise PackageError('Source tree is dirty')
    output=args.output.expanduser().resolve()
    if output.exists():raise PackageError('Output exists; refusing overwrite')
    data,manifest=make_package(ROOT,commit)
    second,_=make_package(ROOT,commit)
    if data!=second:raise PackageError('Double build not byte-identical')
    output.mkdir(parents=True,mode=0o700)
    filename=f'passwords_otp-{VERSION}.zip'
    (output/filename).write_bytes(data)
    (output/(filename+'.sha256')).write_text(digest(data)+'  '+filename+'\n')
    (output/'BUILD.json').write_bytes(canonical_json(manifest))
    print('PACKAGE_PASS source='+commit+' sha256='+digest(data)+' production_approved=false')
if __name__=='__main__':main()
