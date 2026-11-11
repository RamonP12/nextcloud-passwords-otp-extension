#!/usr/bin/env python3
"""Strict deterministic development package. No installation or network access."""
from __future__ import annotations
import argparse, hashlib, io, json, os, pathlib, re, stat, subprocess, zipfile
import xml.etree.ElementTree as ET
VERSION='1.0.1'
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=('appinfo/info.xml','appinfo/routes.php','lib/AppInfo/Application.php',
 'lib/Controller/PageController.php','lib/Service/PasswordsAuthAdapter.php','templates/main.php',
 'css/app-101.css','js/app-101.js','img/app.svg','LICENSE','THIRD_PARTY_NOTICES.md','THIRD_PARTY_LICENSES.txt')
OPTIONAL=('js/app-101.js.LEGAL.txt',)
MAX_ARCHIVE=20*1024*1024
MAX_UNPACKED=30*1024*1024
STAMP=(2026,1,1,0,0,0)
class PackageError(ValueError): pass

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def identity(xml:bytes)->tuple[str,str]:
    if b'<!DOCTYPE' in xml or len(xml)>100000:raise PackageError('Unsafe metadata')
    node=ET.fromstring(xml)
    return node.findtext('id',''),node.findtext('version','')

def assert_appinfo_contract(xml:bytes)->None:
    """Fail closed on the v1.0.1 XSD regression; full XSD lint is a separate gate."""
    if identity(xml)!=('passwords_otp',VERSION):raise PackageError('Unexpected app identity/version')
    node=ET.fromstring(xml)
    names=[child.tag for child in node]
    for required in ('id','name','summary','description','version','licence','author','category','bugs','dependencies'):
        if names.count(required)!=1:raise PackageError('Missing or duplicate appinfo XSD required element: '+required)
    category=names.index('category')
    bugs=names.index('bugs')
    repository=names.index('repository') if 'repository' in names else names.index('dependencies')
    dependencies=names.index('dependencies')
    if not (category<bugs<repository<=dependencies):raise PackageError('Appinfo XSD sequence: category/bugs/repository/dependencies')
    if node.findtext('bugs')!='https://github.com/RamonP12/nextcloud-passwords-otp-extension/issues':
        raise PackageError('Unexpected issue-tracker URL in appinfo')

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

RUNTIME_DEPENDENCIES={
    'eventemitter3':('3.1.2','MIT'),
    'libsodium-sumo':('0.8.4','ISC'),
    'libsodium-wrappers-sumo':('0.8.4','ISC'),
    'passwords-client':('1.0.0-beta.6117','ISC'),
    'process':('0.11.10','MIT'),
    'querystringify':('2.2.0','MIT'),
    'requires-port':('1.0.0','MIT'),
    'url-parse':('1.5.10','MIT'),
}
# The pinned passwords-client package has no LICENSE file. Its metadata declares
# ISC and author Marius Wieschollek. This attribution is reconstructed and is
# NOT presented as an original upstream license file.
ISC_PASSWORDS_CLIENT_NOTICE='''Copyright (c) Marius Wieschollek

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
'''

def third_party_license_bundle(root:pathlib.Path)->bytes:
    """Bundle original notices from the exact locked runtime packages.

    This runs only during package creation, never AIO validation/extraction,
    which must remain usable without a Node.js/npm installation.
    """
    try:
        lock=json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
        packages=lock['packages']
        if lock['lockfileVersion']!=3 or packages['']['version']!=VERSION:
            raise PackageError('Unexpected lockfile format/version')
        found=set()
        pending=list(packages[''].get('dependencies',{}))
        while pending:
            name=pending.pop()
            if name in found:continue
            if name not in RUNTIME_DEPENDENCIES:
                raise PackageError('Unreviewed runtime dependency: '+str(name))
            entry=packages.get('node_modules/'+name)
            if not isinstance(entry,dict):raise PackageError('Missing locked runtime dependency: '+name)
            version,license_id=RUNTIME_DEPENDENCIES[name]
            if entry.get('version')!=version or entry.get('license')!=license_id:
                raise PackageError('Changed runtime dependency license/version: '+name)
            found.add(name)
            pending.extend(entry.get('dependencies',{}))
            pending.extend(entry.get('optionalDependencies',{}))
        if found!=RUNTIME_DEPENDENCIES.keys():
            raise PackageError('Runtime dependency set differs from license inventory')
        sections=[
            'Third-party license notices for passwords_otp '+VERSION,
            'These are runtime package notices; esbuild is a build tool and is not bundled.',
            'The pinned passwords-client package has no LICENSE file in the inspected installation.',
            'Its ISC notice below is reconstructed from the declared license and author metadata.',
            '',
        ]
        for name in sorted(found):
            version,license_id=RUNTIME_DEPENDENCIES[name]
            directory=root/'node_modules'/name
            metadata_file=directory/'package.json'
            if directory.is_symlink() or not directory.is_dir() or metadata_file.is_symlink() or not metadata_file.is_file():
                raise PackageError('Untrusted/missing installed dependency: '+name)
            metadata=json.loads(metadata_file.read_text(encoding='utf-8'))
            if metadata.get('name')!=name or metadata.get('version')!=version or metadata.get('license')!=license_id:
                raise PackageError('Installed dependency does not match lockfile: '+name)
            license_text=None;license_source=None
            for filename in ('LICENSE','LICENSE.md','LICENSE.txt','LICENCE','LICENCE.md','COPYING','NOTICE'):
                candidate=directory/filename
                if candidate.is_symlink():raise PackageError('Symlink license notice is forbidden: '+name)
                if candidate.is_file():
                    content=candidate.read_bytes()
                    if not 100<=len(content)<=131072:raise PackageError('Invalid license size: '+name)
                    license_text=content.decode('utf-8-sig')
                    license_source='Original npm package file: '+filename
                    break
            if license_text is None:
                if name!='passwords-client' or version!='1.0.0-beta.6117':
                    raise PackageError('Missing original license file: '+name)
                author=metadata.get('author','')
                if isinstance(author,dict):author=author.get('name','')
                if not isinstance(author,str) or 'Wieschollek' not in author:
                    raise PackageError('Missing expected upstream author metadata for ISC fallback')
                license_text=ISC_PASSWORDS_CLIENT_NOTICE
                license_source='Reconstructed standard ISC notice; not an original upstream LICENSE file'
            if not re.search(r'copyright',license_text,re.I) or 'Permission' not in license_text or 'THE SOFTWARE IS PROVIDED' not in license_text:
                raise PackageError('Incomplete third-party license notice: '+name)
            sections.extend(['-'*72,f'{name}@{version} | {license_id}',license_source,'',license_text.rstrip(),''])
        return ('\n'.join(sections).rstrip()+'\n').encode('utf-8')
    except (OSError,UnicodeError,KeyError,TypeError,json.JSONDecodeError) as error:
        raise PackageError('Cannot assemble third-party licenses: '+str(error)) from error

def make_package(root:pathlib.Path,commit:str)->tuple[bytes,dict]:
    if not re.fullmatch(r'[0-9a-f]{40}',commit):raise PackageError('Invalid source commit')
    files={}
    for relative in RUNTIME+OPTIONAL:
        if relative=='THIRD_PARTY_LICENSES.txt':
            files[relative]=third_party_license_bundle(root)
            continue
        path=root/relative
        if relative in OPTIONAL and not path.exists():continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):raise PackageError('Unsafe/missing runtime input: '+relative)
        files[relative]=path.read_bytes()
    assert_appinfo_contract(files['appinfo/info.xml'])
    js=files['js/app-101.js']
    if len(js)<10000 or b'PASSWORDS_OTP_JS_101_VERIFIED' not in js:raise PackageError('Fresh production bundle missing')
    if b'PASSWORDS_OTP_CSS_101_VERIFIED' not in files['css/app-101.css']:raise PackageError('CSS marker missing')
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
    if expected!=manifest.get('files'):raise PackageError('Manifest file integrity mismatch')
    assert_appinfo_contract(files['appinfo/info.xml'])
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
