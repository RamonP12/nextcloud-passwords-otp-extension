#!/usr/bin/env python3
"""Transactional upgrade of the specifically named, localhost-only laptop fixture.
Does not deploy to production. Changes only passwords_otp files/app configuration.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, pathlib, re, shutil, ssl, subprocess, sys, tempfile, time, urllib.request, uuid
from release import VERSION, PackageError, validate_package, extract_checked, identity, digest, canonical_json, safe_relative
LIVE='/var/www/html/custom_apps/passwords_otp'
PHP='passwords-php'; NGINX='passwords-nginx'
class DeploymentError(RuntimeError):pass
class RolledBack(DeploymentError):pass

SUPPORTED_ASSETS = {'0.6.1': 'ap061', '0.7.0': 'app-070', '0.7.1': 'app-071', '0.7.2': 'app-072', '0.7.3': 'app-073', '1.0.0': 'app-100', '1.0.1': 'app-100'}
def asset_for_version(version:str)->str:
    try:return SUPPORTED_ASSETS[version]
    except KeyError:raise DeploymentError('Unsupported OTP asset version') from None

def file_hashes(root:pathlib.Path)->dict[str,str]:
    result={}
    if root.is_symlink() or not root.is_dir():raise DeploymentError('Unsafe backup root')
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise DeploymentError('Backup contains a symlink')
        if path.is_file():
            name=path.relative_to(root).as_posix()
            if not safe_relative(name) or not re.fullmatch(r'[A-Za-z0-9_./-]+',name):raise DeploymentError('Unsafe backup filename')
            result[name]=digest(path.read_bytes())
    if not result:raise DeploymentError('Empty app backup')
    return result

def transaction(backend,source:pathlib.Path,version:str,expected:dict[str,str],backup_root:pathlib.Path)->pathlib.Path:
    before=backend.preflight()
    transaction_id=uuid.uuid4().hex
    backup=backup_root/transaction_id
    backup.mkdir(parents=True,mode=0o700,exist_ok=False)
    state={'schema':1,'transaction':transaction_id,'phase':'preflight','before':before,
        'target_version':version,'target_files':expected,'production':False}
    def journal(phase):
        state['phase']=phase
        temporary=backup/'transaction.tmp';temporary.write_bytes(canonical_json(state));temporary.chmod(0o600)
        with temporary.open('rb')as f:os.fsync(f.fileno())
        temporary.replace(backup/'transaction.json')
    changed=False
    try:
        backend.prepare(transaction_id,source,expected)
        journal('staged')
        backend.backup(backup/'passwords_otp')
        if file_hashes(backup/'passwords_otp')!=before['files']:raise DeploymentError('Backup verification failed')
        journal('backup-verified');print('BACKUP_PASS:',backup,flush=True)
        changed=True  # A failed command may nevertheless have disabled the app.
        journal('disabling');backend.disable()
        journal('swapping');backend.swap(transaction_id)
        journal('activating');backend.activate(version,before['enabled'])
        backend.restart();backend.verify(version,expected,before)
        journal('installed');print('INSTALL_PASS: version='+version,flush=True)
        return backup
    except BaseException as cause:
        if changed:
            try:
                journal('recovering');backend.restore(transaction_id,before)
                backend.restart();backend.verify(before['version'],before['files'],before)
                journal('rolled-back');print('ROLLBACK_PASS: previous app restored',flush=True)
            except BaseException:
                journal('recovery-failed')
                raise DeploymentError('Installation and automatic rollback failed. Stop; preserve backup: '+str(backup)) from cause
            raise RolledBack('Installation failed; previous app was restored. Backup: '+str(backup)) from cause
        journal('aborted-before-mutation')
        raise
    finally:
        # Keep previous/failed app copies and the host journal for explicit recovery.
        # Only the unused staging directory of this transaction may be removed.
        try:backend.cleanup_stage(transaction_id)
        except Exception:pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise DeploymentError('Unexpected HTTPS redirect')

class DockerBackend:
    def run(self,args:list[str],*,timeout:int=120)->str:
        try:
            result=subprocess.run(args,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
            return result.stdout.strip()
        except (subprocess.SubprocessError,OSError)as error:
            # Never relay generic upstream output into a support log.
            raise DeploymentError('Command failed: '+args[0]+' '+(args[1]if len(args)>1 else '')) from error
    def exec(self,*args:str)->str:return self.run(['docker','exec','-u','root',PHP,*args])
    def occ(self,*args:str)->str:return self.run(['docker','exec','-u','www-data','-e','XDEBUG_MODE=off',PHP,'php','/var/www/html/occ',*args])
    def config(self,key:str)->str:return self.occ('config:app:get','passwords_otp',key)
    def inspect(self,name:str)->dict:return json.loads(self.run(['docker','inspect',name]))[0]
    @staticmethod
    def mount_location(container:dict,path:str)->tuple[str,str]:
        matches=[m for m in container.get('Mounts',[]) if path==m['Destination'] or path.startswith(m['Destination'].rstrip('/')+'/')]
        if not matches:raise DeploymentError('App is not on a shared, explicit mount')
        selected=max(matches,key=lambda m:len(m['Destination']))
        suffix=path.removeprefix(selected['Destination']).lstrip('/')
        return selected['Type'],str(pathlib.PurePosixPath(selected['Source'])/suffix)
    def remote_hashes(self,path:str)->dict[str,str]:
        code='''$r=$argv[1];if(is_link($r)||!is_dir($r))exit(2);$a=[];$n=0;$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($r,FilesystemIterator::SKIP_DOTS));foreach($it as $f){if($f->isLink())exit(3);if($f->isFile()){$p=substr($f->getPathname(),strlen($r)+1);if(!preg_match("~^[A-Za-z0-9_./-]+$~",$p))exit(4);$n+=$f->getSize();if($n>31457280)exit(5);$a[$p]=hash_file("sha256",$f->getPathname());}}ksort($a);echo json_encode($a,JSON_THROW_ON_ERROR);'''
        return json.loads(self.exec('php','-r',code,'--',path))
    def preflight(self)->dict:
        override=os.environ.get('DOCKER_HOST','')
        context=os.environ.get('DOCKER_CONTEXT','')
        if context and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',context):raise DeploymentError('Invalid Docker context name')
        contexts=json.loads(self.run(['docker','context','inspect',*([context]if context else [])]))
        # DOCKER_CONTEXT takes precedence over DOCKER_HOST in the Docker CLI.
        host=contexts[0]['Endpoints']['docker']['Host']if context else override or contexts[0]['Endpoints']['docker']['Host']
        if not host.startswith('unix://'):raise DeploymentError('Only a local Unix Docker endpoint is permitted')
        php=self.inspect(PHP);nginx=self.inspect(NGINX)
        if not php['State']['Running'] or not nginx['State']['Running']:raise DeploymentError('Fixture containers are not running')
        for container in (php,nginx):
            for published in container.get('NetworkSettings',{}).get('Ports',{}).values():
                if any(binding.get('HostIp')not in ('127.0.0.1','::1')for binding in (published or [])):raise DeploymentError('Fixture has a non-loopback published port')
        image=php['Config']['Image']
        if not (image.startswith('nextcloud:') or image=='passwords-folder-sharing-work-app'):raise DeploymentError('Unexpected laptop PHP image')
        bindings=nginx.get('NetworkSettings',{}).get('Ports',{}).get('443/tcp')or[]
        if not bindings or any(x.get('HostIp')not in ('127.0.0.1','::1')or x.get('HostPort')!='443'for x in bindings):
            raise DeploymentError('HTTPS fixture must be bound exclusively to localhost:443')
        if self.mount_location(php,LIVE)!=self.mount_location(nginx,LIVE):raise DeploymentError('PHP/nginx do not share the same app path; no blind file synchronization')
        status=json.loads(self.occ('status','--output=json'))
        if status.get('installed')is not True or status.get('maintenance')is not False or not str(status.get('versionstring','')).startswith('35.'):
            raise DeploymentError('Not an installed, non-maintenance Nextcloud 35 fixture')
        if 'localhost' not in self.occ('config:system:get','trusted_domains').splitlines():raise DeploymentError('localhost trusted domain missing')
        apps=json.loads(self.occ('app:list','--output=json'));enabled=apps.get('enabled',{})
        if 'passwords'not in enabled or 'passwords_otp'not in enabled:raise DeploymentError('Both original Passwords and existing OTP app must be enabled')
        app_id,version=identity(self.exec('cat',LIVE+'/appinfo/info.xml').encode())
        if app_id!='passwords_otp':raise DeploymentError('Existing app identity mismatch')
        if version not in SUPPORTED_ASSETS:raise DeploymentError('Unsupported existing OTP version')
        installed=self.config('installed_version');scope=self.config('enabled')
        if installed!=version:raise DeploymentError('Installed version and app metadata differ')
        # This installer is deliberately limited to the known isolated laptop profile.
        # Refuse group-scoped apps rather than accidentally broadening their permissions.
        if scope!='yes':raise DeploymentError('Group-scoped/disabled deployment is unsupported; no changes performed')
        files=self.remote_hashes(LIVE)
        if any('/Migration/'in p or p=='appinfo/database.xml'for p in files):raise DeploymentError('Schema-changing app cannot use this rollback procedure')
        return {'version':version,'installed_version':installed,'enabled':scope,'files':files,
            'nextcloud':status['versionstring'],'passwords':enabled['passwords'],'container_id':php['Id']}
    @staticmethod
    def paths(transaction_id:str)->tuple[str,str,str]:
        if not re.fullmatch(r'[0-9a-f]{32}',transaction_id):raise DeploymentError('Invalid transaction ID')
        root='/var/www/html/custom_apps/.otp-release/'+transaction_id
        return root+'/stage',root+'/previous',root+'/failed'
    def prepare(self,transaction_id:str,source:pathlib.Path,expected:dict[str,str])->None:
        stage,previous,failed=self.paths(transaction_id)
        self.exec('sh','-ec','test ! -L /var/www/html/custom_apps/.otp-release; test ! -e "$1"; test ! -L "$1"; mkdir -p "$1"; chmod 0700 /var/www/html/custom_apps/.otp-release "$(dirname "$1")"; test "$(stat -c %d "$1")" = "$(stat -c %d "$2")"','--',stage,LIVE)
        self.run(['docker','cp',str(source)+ '/.',PHP+':'+stage])
        self.exec('sh','-ec','''app="$1"; chown -R www-data:www-data "$app"; find "$app" -type d -exec chmod 0700 {} +; find "$app" -type f -exec chmod 0600 {} +; chmod 0755 "$app"; for dir in css js img; do test -d "$app/$dir"; find "$app/$dir" -type d -exec chmod 0755 {} +; find "$app/$dir" -type f -exec chmod 0644 {} +; done''','--',stage)
        if self.remote_hashes(stage)!=expected:raise DeploymentError('Staged file integrity mismatch')
    def backup(self,destination:pathlib.Path)->None:
        destination.mkdir(mode=0o700)
        self.run(['docker','cp',PHP+':'+LIVE+'/.',str(destination)])
    def disable(self)->None:self.occ('app:disable','passwords_otp')
    def swap(self,transaction_id:str)->None:
        stage,previous,_=self.paths(transaction_id)
        self.exec('sh','-ec','''test -d "$1"; test -d "$2"; test ! -L "$2"; test ! -e "$3"; test ! -L "$3"; mv -- "$2" "$3"; if ! mv -- "$1" "$2"; then mv -- "$3" "$2"; exit 1; fi''','--',stage,LIVE,previous)
    def activate(self,version:str,enabled:str)->None:
        if enabled!='yes':raise DeploymentError('Unexpected app enablement scope')
        self.occ('app:enable','passwords_otp')
        if self.config('installed_version')!=version:raise DeploymentError('App activation version mismatch')
    def restart(self)->None:
        self.run(['docker','restart',PHP])
        for attempt in range(30):
            try:
                status=json.loads(self.occ('status','--output=json'))
                if status.get('installed')is True and status.get('maintenance')is False:return
            except (DeploymentError,ValueError):pass
            time.sleep(1)
        raise DeploymentError('Local PHP/Nextcloud did not become ready')
    def verify(self,version:str,expected:dict[str,str],before:dict)->None:
        if self.remote_hashes(LIVE)!=expected:raise DeploymentError('Installed files changed')
        apps=json.loads(self.occ('app:list','--output=json')).get('enabled',{})
        if apps.get('passwords')!=before['passwords']or apps.get('passwords_otp')!=version:raise DeploymentError('App availability/version mismatch')
        if self.config('enabled')!=before['enabled']or self.config('installed_version')!=version:raise DeploymentError('App configuration mismatch')
        if identity(self.exec('cat',LIVE+'/appinfo/info.xml').encode())!=('passwords_otp',version):raise DeploymentError('Installed identity mismatch')
        asset=asset_for_version(version)
        opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
        for kind in ('css','js'):
            relative=kind+'/'+asset+'.'+kind
            request=urllib.request.Request('https://localhost/custom_apps/passwords_otp/'+relative,headers={'Cache-Control':'no-cache'})
            with opener.open(request,timeout=10)as response:
                data=response.read(20*1024*1024)
                if response.status!=200 or digest(data)!=expected.get(relative):raise DeploymentError('Served asset mismatch: '+kind)
        print('HTTP_ASSETS_PASS:',asset,flush=True)
    def restore(self,transaction_id:str,before:dict)->None:
        stage,previous,failed=self.paths(transaction_id)
        try:self.disable()
        except DeploymentError:pass
        # Restore only this transaction's saved tree. If swap never occurred, keep the original.
        self.exec('sh','-ec','''if test -d "$2"; then test ! -e "$3"; test ! -L "$3"; if test -e "$1"; then mv -- "$1" "$3"; fi; mv -- "$2" "$1"; fi; test -d "$1"''','--',LIVE,previous,failed)
        if self.remote_hashes(LIVE)!=before['files']:raise DeploymentError('Cannot identify original files for rollback')
        # Only own app configuration, and only for the schema-less supported versions.
        self.occ('config:app:set','passwords_otp','installed_version','--value='+before['installed_version'])
        self.activate(before['version'],before['enabled'])
    def cleanup_stage(self,transaction_id:str)->None:
        stage,_,_=self.paths(transaction_id)
        self.exec('sh','-ec','test ! -L "$1"; if test -d "$1"; then rm -rf -- "$1"; fi','--',stage)

def rollback_successful(backend,backup:pathlib.Path)->None:
    state=json.loads((backup/'transaction.json').read_text())
    if state.get('schema')!=1 or state.get('phase')!='installed' or state.get('production')is not False:
        raise DeploymentError('Only a verified completed installation can use explicit rollback')
    transaction_id=state['transaction'];DockerBackend.paths(transaction_id)
    before=state['before']
    if file_hashes(backup/'passwords_otp')!=before['files']:raise DeploymentError('Host backup integrity mismatch')
    current=backend.preflight()
    if current['files']!=state['target_files']or current['version']!=state['target_version']or current['passwords']!=before['passwords']:
        raise DeploymentError('Current installation differs from transaction; refusing stale rollback')
    backend.restore(transaction_id,before);backend.restart();backend.verify(before['version'],before['files'],before)
    state['phase']='restored-manually';(backup/'transaction.json').write_bytes(canonical_json(state))
    print('ROLLBACK_PASS: previous app restored; original Passwords retained')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=pathlib.Path,nargs='?');parser.add_argument('--sha256')
    parser.add_argument('--rollback',type=pathlib.Path);parser.add_argument('--localhost-test-only',action='store_true')
    parser.add_argument('--backup-root',type=pathlib.Path,default=pathlib.Path.home()/'Downloads/passwords-otp-backups')
    args=parser.parse_args()
    if not args.localhost_test_only:parser.error('Explicit --localhost-test-only is required')
    os.umask(0o077)
    if args.rollback:
        if args.archive or args.sha256:parser.error('Rollback cannot be combined with installation')
        rollback_successful(DockerBackend(),args.rollback.expanduser().resolve());return
    if not args.archive or not args.sha256:parser.error('Archive and --sha256 required for installation')
    data=args.archive.read_bytes();files,manifest=validate_package(data,args.sha256)
    with tempfile.TemporaryDirectory(prefix='passwords-otp-stage-')as temporary:
        source=pathlib.Path(temporary)/'passwords_otp';extract_checked(files,source)
        backup=transaction(DockerBackend(),source,manifest['version'],{key:digest(value)for key,value in files.items()},args.backup_root.expanduser().resolve())
    print('Backup and transaction journal:',backup)
    print('Browser: https://localhost/apps/passwords_otp/ (hard reload). No production approval.')
if __name__=='__main__':
    try:main()
    except (DeploymentError,PackageError,ValueError,OSError)as error:
        print('STOP:',str(error),file=sys.stderr);sys.exit(1)
