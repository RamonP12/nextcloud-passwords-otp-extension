#!/usr/bin/env python3
"""Strict deterministic development package. No installation or network access."""
from __future__ import annotations
import argparse, hashlib, io, json, os, pathlib, re, stat, subprocess, zipfile
import xml.etree.ElementTree as ET
VERSION='1.2.0-dev'
ROOT=pathlib.Path(__file__).resolve().parents[1]
JS_ASSET='js/app-120-dev.mjs'
CSS_ASSET='css/app-120-dev.css'
PASSWORDS_POLICY='lib/Service/PasswordsDependency.php'
RUNTIME=('appinfo/info.xml','appinfo/routes.php','lib/AppInfo/Application.php',
 'lib/Controller/PageController.php','lib/Service/PasswordsAuthAdapter.php',
 PASSWORDS_POLICY,
 'lib/BackgroundJob/CheckPasswordsDependency.php',
 'lib/Migration/Version010102Date20261119000000.php','lib/Migration/RemoveDependencyJob.php','templates/main.php',
 CSS_ASSET,JS_ASSET,'img/app.svg','LICENSE','THIRD_PARTY_NOTICES.md','THIRD_PARTY_LICENSES.txt')
OPTIONAL=()
LICENSE_INVENTORY='scripts/runtime-licenses.json'
BUNDLE_METADATA='.build/bundle-modules.json'
MAX_ARCHIVE=20*1024*1024
MAX_UNPACKED=30*1024*1024
STAMP=(2026,1,1,0,0,0)
class PackageError(ValueError): pass

def reviewed_passwords_version(files: dict[str, bytes] | None = None) -> str:
    # Read the exact reviewed build from the checkout or a verified archive.
    if files is None:
        policy = checked_file(ROOT, PASSWORDS_POLICY).read_bytes()
    else:
        policy = files[PASSWORDS_POLICY]
    versions = re.findall(rb"^    public const REVIEWED_VERSION = '([0-9]{4}\.[0-9]{2}\.[0-9]0)';$", policy, re.M)
    if len(versions) != 1:
        raise PackageError('Missing or ambiguous reviewed Passwords release line')
    return versions[0].decode('ascii')


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

def dependency_name(path:str)->str:
    """The name after the final node_modules segment, including an npm scope."""
    return path.rsplit('node_modules/',1)[-1]


def runtime_packages(lock:dict)->dict[str,dict]:
    """Resolve the production graph using npm's nearest-node_modules lookup.

    Include required peers and distinguish nested versions by lockfile path.
    Optional peers are not followed: browser bundle-module verification below
    prevents an unreviewed optional peer from entering emitted assets. A dev flag is not used as a security boundary:
    a production dependency must still be inventoried if npm labels it dev.
    """
    packages=lock.get('packages',{})
    if lock.get('lockfileVersion')!=3 or packages.get('',{}).get('version')!=VERSION:
        raise PackageError('Unexpected lockfile format/version')
    def resolve(parent,name):
        if not isinstance(name,str) or not re.fullmatch(r'(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+',name):
            raise PackageError('Unsafe dependency name')
        base=parent
        while True:
            candidate=(base+'/' if base else '')+'node_modules/'+name
            if candidate in packages:return candidate
            if not base:break
            base=base.rsplit('/node_modules/',1)[0] if '/node_modules/' in base else ''
        raise PackageError('Missing locked runtime dependency: '+name)
    found={}
    pending=[('',packages[''])]
    while pending:
        parent,entry=pending.pop()
        ordinary=dict(entry.get('dependencies',{}))
        optional=entry.get('optionalDependencies',{})
        peers=entry.get('peerDependencies',{})
        peer_meta=entry.get('peerDependenciesMeta',{})
        for name in sorted(set(ordinary)|set(optional)|set(peers)):
            # Optional build integrations must not pull Vite/native binaries
            # into the browser notice set. Actual bundle inputs are also gated.
            optional_peer=name in peers and name not in ordinary and name not in optional \
                and peer_meta.get(name,{}).get('optional') is True
            if optional_peer:continue
            path=resolve(parent,name)
            if path in found:continue
            record=packages[path]
            if not isinstance(record,dict) or record.get('link') is True:
                raise PackageError('Linked/invalid runtime dependency: '+path)
            found[path]=record
            pending.append((path,record))
    return dict(sorted(found.items()))


def checked_file(root:pathlib.Path,relative:str,allow_absent_package=False)->pathlib.Path|None:
    if not safe_relative(relative):raise PackageError('Unsafe dependency file path')
    path=root/relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise PackageError('Dependency file escapes source root: '+relative)
    current=root
    for part in pathlib.PurePosixPath(relative).parts:
        current=current/part
        if current.is_symlink():raise PackageError('Symlink dependency file is forbidden: '+relative)
    if allow_absent_package and not path.parent.exists():return None
    if not path.is_file():raise PackageError('Missing dependency file: '+relative)
    return path


def third_party_license_bundle(root:pathlib.Path,bundled_packages:set[str])->bytes:
    """Collect exact, reviewed original notices for the runtime closure.

    The checked-in inventory pins metadata, tarball integrity and notice hashes.
    It includes installed transitive production packages even when eliminated by
    tree shaking. An absent optional-only package can be skipped after bundle verification. Dev-only build tools are not shipped.
    Validation/extraction of an already built ZIP requires no npm installation.
    """
    try:
        lock=json.loads(checked_file(root,'package-lock.json').read_text(encoding='utf-8'))
        found=runtime_packages(lock)
        inventory=json.loads(checked_file(root,LICENSE_INVENTORY).read_text(encoding='utf-8'))
        if inventory.get('schema')!=1 or inventory.get('app_version')!=VERSION:
            raise PackageError('Unexpected runtime license inventory schema/version')
        reviewed=inventory.get('packages',{})
        if not isinstance(reviewed,dict):raise PackageError('Invalid runtime license inventory')
        if found.keys()!=reviewed.keys():
            raise PackageError('Unreviewed runtime dependency set differs from license inventory')
        sections=[
            'Third-party license notices for passwords_otp '+VERSION,
            'Conservative production dependency graph, including required peers and nested versions.',
            'Build-only tools (Vite, esbuild and their development dependencies) are not shipped.',
            'The pinned passwords-client ISC notice is reconstructed; all other notices are original package or pinned upstream files.',
            '',
        ]
        for path,entry in found.items():
            record=reviewed[path]
            if not isinstance(record,dict):raise PackageError('Invalid runtime license record: '+path)
            name=dependency_name(path)
            version,license_id=entry.get('version'),entry.get('license')
            if any(record.get(k)!=v for k,v in {'name':name,'version':version,
                    'license':license_id,'integrity':entry.get('integrity')}.items()) \
                    or not isinstance(entry.get('integrity'),str) or not entry['integrity'].startswith('sha512-'):
                raise PackageError('Changed runtime dependency license/version/integrity: '+path)
            package_json=checked_file(root,path+'/package.json',
                allow_absent_package=entry.get('optional') is True and path not in bundled_packages)
            if package_json is None:continue
            metadata=json.loads(package_json.read_text(encoding='utf-8'))
            if metadata.get('name')!=name or metadata.get('version')!=version or metadata.get('license')!=license_id:
                raise PackageError('Installed dependency does not match lockfile: '+path)
            sections.extend(['-'*72,f'{name}@{version} | {license_id}', 'Lockfile path: '+path,''])
            notices=record.get('notices')
            if record.get('notice_policy')=='unbundled-only':
                if notices!=[] or not record.get('review_note'):
                    raise PackageError('Invalid unbundled-only license record: '+path)
                sections.extend(['NOT BUNDLED. '+record['review_note'],
                    'The package gate rejects any emitted browser module from this package.',''])
                continue
            if record.get('notice_policy')=='reconstructed-passwords-client-isc':
                if name!='passwords-client' or version!='1.0.0-beta.6117' or license_id!='ISC' or notices!=[]:
                    raise PackageError('Invalid reconstructed license exception')
                author=metadata.get('author','')
                if isinstance(author,dict):author=author.get('name','')
                if not isinstance(author,str) or 'Wieschollek' not in author:
                    raise PackageError('Missing expected upstream author metadata for ISC fallback')
                sections.extend(['Reconstructed standard ISC notice; not an original upstream LICENSE file',
                    '',ISC_PASSWORDS_CLIENT_NOTICE.rstrip(),''])
                continue
            if not isinstance(notices,list) or not notices:
                raise PackageError('Missing original license file inventory: '+path)
            filenames=set()
            for notice in notices:
                if not isinstance(notice,dict):raise PackageError('Invalid license notice: '+path)
                filename=notice.get('file')
                source_file=notice.get('source_file')
                if bool(filename)==bool(source_file):raise PackageError('Ambiguous license notice source: '+path)
                if source_file:
                    url=notice.get('url','')
                    if not re.fullmatch(r'https://raw\.githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/.+',url):
                        raise PackageError('Original upstream notice lacks immutable source URL: '+path)
                    if not source_file.startswith('licenses/npm/'):
                        raise PackageError('Invalid upstream notice source path: '+path)
                    relative=source_file
                    source='Original upstream file: '+url
                else:
                    relative=path+'/'+filename
                    source='Original npm package file: '+filename
                if relative in filenames:raise PackageError('Duplicate license notice: '+path)
                filenames.add(relative)
                content=checked_file(root,relative).read_bytes()
                if not 100<=len(content)<=524288 or digest(content)!=notice.get('sha256'):
                    raise PackageError('Original license notice changed/incomplete: '+relative)
                # Hashes pin the exact reviewed text, including Apache/OFL/BSD
                # and supplemental NOTICE files. No MIT-only phrase heuristic.
                sections.extend([source,'',content.decode('utf-8-sig').rstrip(),''])
        return ('\n'.join(sections).rstrip()+'\n').encode('utf-8')
    except (OSError,UnicodeError,KeyError,TypeError,json.JSONDecodeError) as error:
        raise PackageError('Cannot assemble third-party licenses: '+str(error)) from error


def build_source_inputs(root:pathlib.Path)->dict[str,str]:
    """Complete frontend input set, independent of the bundler's import graph.

    Hash unused source files too: a new or removed module must invalidate old
    output just as an edited module does. Docs/tests/PHP are not compiled inputs.
    """
    source=root/'src'
    if source.is_symlink() or not source.is_dir():raise PackageError('Unsafe/missing frontend source directory')
    paths=['package.json','package-lock.json','vite.config.js']
    for path in sorted(source.rglob('*')):
        if path.is_symlink():raise PackageError('Symlink frontend source is forbidden')
        if path.is_file():paths.append(path.relative_to(root).as_posix())
        elif not path.is_dir():raise PackageError('Nonregular frontend source is forbidden')
    if len(paths)==3:raise PackageError('Frontend source tree is empty')
    return {path:digest(checked_file(root,path).read_bytes()) for path in sorted(paths)}


def validate_bundle_metadata(root:pathlib.Path,files:dict[str,bytes])->dict:
    """Bind build-generated module provenance to both exact emitted assets.

    This closes the optional-peer gap in the conservative package graph: any
    npm package that actually contributes code must be in the reviewed list.
    Vite's build plugin emits this file; package assembly never reconstructs it.
    """
    try:
        metadata=json.loads(checked_file(root,BUNDLE_METADATA).read_text(encoding='utf-8'))
        expected={name:digest(files[name]) for name in (JS_ASSET,CSS_ASSET)}
        if metadata.get('schema')!=2 or metadata.get('assets')!=expected:
            raise PackageError('Bundle metadata does not match emitted assets')
        if metadata.get('mode')!='production' or metadata.get('command')!='build':
            raise PackageError('Only a production build can be packaged')
        source_inputs=build_source_inputs(root)
        if metadata.get('source_inputs')!=source_inputs:
            raise PackageError('Frontend source/config/lock changed after compilation; rebuild required')
        modules=metadata.get('modules')
        build_modules=metadata.get('build_modules')
        if not isinstance(modules,list) or not modules or not all(isinstance(x,str) for x in modules) \
                or len(modules)!=len(set(modules)):
            raise PackageError('Missing/duplicate bundle module inventory')
        if not isinstance(build_modules,list) or not build_modules \
                or not all(isinstance(x,str) for x in build_modules) or len(build_modules)!=len(set(build_modules)):
            raise PackageError('Missing/duplicate complete build module inventory')
        if sorted(modules)!=sorted(x for x in build_modules if x.startswith('node_modules/')):
            raise PackageError('Dependency module inventory is incomplete')
        app_modules=[]
        for module in build_modules:
            if not safe_relative(module) or not module.startswith(('src/','node_modules/')):
                raise PackageError('Unapproved source/fixture in production bundle: '+module)
            if module.startswith('src/'):
                if module not in source_inputs:raise PackageError('Application module is outside source inventory')
                app_modules.append(module)
            checked_file(root,module)
        if not app_modules:raise PackageError('Production bundle has no application source')
        inventory=json.loads(checked_file(root,LICENSE_INVENTORY).read_text(encoding='utf-8'))['packages']
        used=set()
        for module in modules:
            if not isinstance(module,str) or not safe_relative(module) or not module.startswith('node_modules/'):
                raise PackageError('Unsafe bundle module path')
            parts=module.split('/')
            index=max(i for i,part in enumerate(parts) if part=='node_modules')
            end=index+3 if parts[index+1].startswith('@') else index+2
            if len(parts)<=end:raise PackageError('Bundle module does not name a file')
            package='/'.join(parts[:end])
            if package not in inventory:raise PackageError('Unreviewed package in browser bundle: '+package)
            if inventory[package].get('notice_policy')=='unbundled-only':
                raise PackageError('Runtime package lacks reviewed original notice: '+package)
            checked_file(root,module)
            used.add(package)
        return {'module_count':len(modules),'app_module_count':len(app_modules),
                'source_input_count':len(source_inputs),'source_inputs_sha256':digest(canonical_json(source_inputs)),
                'packages':sorted(used)}
    except (OSError,UnicodeError,KeyError,TypeError,IndexError,json.JSONDecodeError) as error:
        raise PackageError('Cannot verify bundle metadata: '+str(error)) from error

def make_package(root:pathlib.Path,commit:str)->tuple[bytes,dict]:
    if not re.fullmatch(r'[0-9a-f]{40}',commit):raise PackageError('Invalid source commit')
    files={}
    for relative in RUNTIME+OPTIONAL:
        if relative=='THIRD_PARTY_LICENSES.txt':
            continue
        path=root/relative
        if relative in OPTIONAL and not path.exists():continue
        files[relative]=checked_file(root,relative).read_bytes()
    if identity(files['appinfo/info.xml'])!=('passwords_otp',VERSION):raise PackageError('Unexpected app identity/version')
    js=files[JS_ASSET]
    if len(js)<10000 or b'PASSWORDS_OTP_JS_120_DEV_VERIFIED' not in js:raise PackageError('Fresh production bundle missing')
    if b'PASSWORDS_OTP_CSS_120_DEV_VERIFIED' not in files[CSS_ASSET]:raise PackageError('CSS marker missing')
    for prohibited in [b'OTP_HOTP_WRITE_TEST_ONLY',b'hotpNext(',b'hotp-commit-uncertain',b'passwords-otp-ap4__']:
        if prohibited in js:raise PackageError('Removed feature leaked into runtime')
    bundle_inputs=validate_bundle_metadata(root,files)
    files['THIRD_PARTY_LICENSES.txt']=third_party_license_bundle(root,set(bundle_inputs['packages']))
    manifest={'schema':1,'app':'passwords_otp','version':VERSION,'source_commit':commit,'channel':'public-source-baseline',
        'production_approved':False,'bundle_inputs':bundle_inputs,
        'files':{key:digest(value) for key,value in sorted(files.items())}}
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
    if data!=second:raise PackageError('Double packaging not byte-identical')
    # The ZIP remains the checked transport for the existing local installer.
    # Distribute a separately verified single-root TAR for manual installation.
    # Neither archive has a Nextcloud signature unless explicitly signed later.
    from appstore_package import manual_archive
    files,_=validate_package(data,digest(data))
    tar=manual_archive(files)
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=commit \
            or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise PackageError('Source checkout changed during packaging')
    output.mkdir(parents=True,mode=0o700)
    filename=f'passwords_otp-{VERSION}.zip'
    (output/filename).write_bytes(data)
    (output/(filename+'.sha256')).write_text(digest(data)+'  '+filename+'\n')
    tarname=f'passwords_otp-{VERSION}.tar.gz'
    (output/tarname).write_bytes(tar)
    (output/(tarname+'.sha256')).write_text(digest(tar)+'  '+tarname+'\n')
    (output/'BUILD.json').write_bytes(canonical_json(manifest))
    print('PACKAGE_PASS source='+commit+' sha256='+digest(data)+' production_approved=false')
    print('TAR_PASS source='+commit+' sha256='+digest(tar)+' nextcloud_signed=false appstore_published=false')
if __name__=='__main__':main()
