<?php
// Public-framework contract doubles. Core-method integration is a separate suite.
declare(strict_types=1);
namespace Psr\Log {
 interface LoggerInterface {public function warning($message,array $context=[]);public function error($message,array $context=[]);}
}
namespace OCP\App {
 class AppPathNotFoundException extends \RuntimeException {}
 interface IAppManager {
  public function getAppInstalledVersions();public function getAppPath($id,$ignoreCache=false);
  public function getAppInfoByPath($path);public function isEnabledForAnyone($id);public function disableApp($id);
 }
}
namespace OCP\EventDispatcher {
 class Event {}
 interface IEventListener {public function handle(Event $event):void;}
}
namespace OCP\App\Events {
 class AppDisableEvent extends \OCP\EventDispatcher\Event {public function __construct(private string $id){}public function getAppId():string{return $this->id;}}
 class AppEnableEvent extends \OCP\EventDispatcher\Event {public function __construct(private string $id,private array $groups=[]){}public function getAppId():string{return $this->id;}public function getGroupIds():array{return $this->groups;}}
 class AppUpdateEvent extends \OCP\EventDispatcher\Event {public function __construct(private string $id){}public function getAppId():string{return $this->id;}}
}
namespace OCP\AppFramework {class App {public function __construct(...$x){}}}
namespace OCP\AppFramework\Bootstrap {
 interface IBootstrap {}
 interface IRegistrationContext {public function registerEventListener($event,$listener);}
 interface IBootContext {public function injectFn(callable $fn);}
}
namespace OCP\AppFramework\Utility {interface ITimeFactory {}}
namespace OCP\BackgroundJob {
 interface IJobList {public function remove($class,$argument=null);public function add($class,$argument=null);}
 abstract class TimedJob {
  public int $interval=0;public bool $parallel=true;
  public function __construct(\OCP\AppFramework\Utility\ITimeFactory $time){}
  public function setInterval($interval){$this->interval=$interval;}
  public function setAllowParallelRuns($parallel){$this->parallel=$parallel;}
  abstract protected function run($argument);
 }
}
namespace OCP\Migration {
 interface IOutput {}
 interface IRepairStep {public function getName();public function run(IOutput $output);}
 abstract class SimpleMigrationStep {public function name():string{return '';}public function changeSchema(IOutput $output,\Closure $schemaClosure,array $options){return null;}}
}
namespace {
 require __DIR__.'/../../lib/AppInfo/Application.php';
 require __DIR__.'/../../lib/Service/PasswordsDependency.php';
 require __DIR__.'/../../lib/Listener/PasswordsLifecycleListener.php';
 require __DIR__.'/../../lib/BackgroundJob/CheckPasswordsDependency.php';
 require __DIR__.'/../../lib/Migration/Version010102Date20261119000000.php';
 require __DIR__.'/../../lib/Migration/RemoveDependencyJob.php';
 use OCA\PasswordsOtp\AppInfo\Application;
 use OCA\PasswordsOtp\Service\PasswordsDependency;
 use OCA\PasswordsOtp\Listener\PasswordsLifecycleListener;
 use OCA\PasswordsOtp\BackgroundJob\CheckPasswordsDependency;
 use OCA\PasswordsOtp\Migration\Version010102Date20261119000000;
 use OCA\PasswordsOtp\Migration\RemoveDependencyJob;
 use OCP\App\Events\AppDisableEvent;
 use OCP\App\Events\AppEnableEvent;
 use OCP\App\Events\AppUpdateEvent;

 $passed=0;$directories=[];
 function check(bool $result,string $label):void {global $passed;if(!$result)throw new \RuntimeException('FAIL: '.$label);++$passed;}
 function rejects(callable $fn,string $label):void {
  try {$fn();}catch(\RuntimeException $e){check(str_contains($e->getMessage(),'Passwords OTP cannot be enabled.'),$label.' has actionable error');return;}
  check(false,$label.' must reject');
 }
 final class FakeApps implements \OCP\App\IAppManager {
  public array $versions=['passwords'=>'2026.11.20','passwords_otp'=>'1.1.1'];
  public ?array $info=['id'=>'passwords','version'=>'2026.11.20'];
  public array $enabled=['passwords'=>true,'passwords_otp'=>true];
  public array $disabled=[];public array $pathCalls=[];
  public bool $missingPath=false;public bool $unavailable=false;public bool $disableFails=false;
  public mixed $onDisable=null;
  public function __construct(public string $path){}
  public function getAppInstalledVersions(){if($this->unavailable)throw new \RuntimeException('PRIVATE-ERROR');return $this->versions;}
  public function getAppPath($id,$ignoreCache=false){$this->pathCalls[]=[$id,$ignoreCache];if($this->missingPath)throw new \OCP\App\AppPathNotFoundException('PRIVATE-PATH');return $this->path;}
  public function getAppInfoByPath($path){return $this->info;}
  public function isEnabledForAnyone($id){return $this->enabled[$id]??false;}
  public function disableApp($id){if($this->disableFails)throw new \RuntimeException('PRIVATE-DATABASE');$this->enabled[$id]=false;$this->disabled[]=$id;if($this->onDisable)($this->onDisable)($id);}
 }
 final class FakeLogger implements \Psr\Log\LoggerInterface {
  public array $messages=[];
  public function warning($message,array $context=[]){$this->messages[]=['warning',$message,$context];}
  public function error($message,array $context=[]){$this->messages[]=['error',$message,$context];}
 }
 final class FakeJobs implements \OCP\BackgroundJob\IJobList {
  public array $removed=[];public array $added=[];
  public function remove($class,$argument=null){$this->removed[]=[$class,$argument];}
  public function add($class,$argument=null){$this->added[]=[$class,$argument];}
 }
 function fixture():array {
  global $directories;
  $path=sys_get_temp_dir().'/passwords-otp-dependency-'.bin2hex(random_bytes(8));
  mkdir($path.'/appinfo',0700,true);file_put_contents($path.'/appinfo/info.xml','<info><id>passwords</id><version>2026.11.20</version></info>');$directories[]=$path;
  $apps=new FakeApps($path);$logger=new FakeLogger();$dep=new PasswordsDependency($apps,$logger);
  $jobs=new FakeJobs();$listener=new PasswordsLifecycleListener($dep,$jobs);
  return compact('path','apps','logger','dep','listener','jobs');
 }
 register_shutdown_function(static function()use(&$directories):void{
  foreach($directories as $path){@unlink($path.'/appinfo/info.xml');@rmdir($path.'/appinfo');@rmdir($path);}
 });
 $f=fixture();check($f['dep']->reason()===null,'tested installed and enabled version accepted');
 check($f['apps']->pathCalls===[['passwords',true]],'bypass stale app path cache');
 $f['dep']->assertInstallable();check($f['apps']->disabled===[],'valid preflight is read-only');
 foreach(['unregistered','missing-path','missing-file','invalid-info','wrong-id','disabled','older','newer','suffix','pending','unavailable'] as $case){
  $f=fixture();$expected='passwords-missing';
  switch($case){
   case 'unregistered':unset($f['apps']->versions['passwords']);break;
   case 'missing-path':$f['apps']->missingPath=true;break;
   case 'missing-file':unlink($f['path'].'/appinfo/info.xml');break;
   case 'invalid-info':$f['apps']->info=null;break;
   case 'wrong-id':$f['apps']->info['id']='other';break;
   case 'disabled':$f['apps']->enabled['passwords']=false;$expected='passwords-disabled';break;
   case 'older':case 'newer':case 'suffix':
    $version=['older'=>'2026.10.1','newer'=>'2026.12.1','suffix'=>'2026.11.20.0'][$case];
    $f['apps']->versions['passwords']=$version;$f['apps']->info['version']=$version;$expected='passwords-incompatible';break;
   case 'pending':$f['apps']->info['version']='2026.12.1';$expected='passwords-update-pending';break;
   case 'unavailable':$f['apps']->unavailable=true;$expected='passwords-unavailable';break;
  }
  check($f['dep']->reason()===$expected,'dependency reason '.$case);
  rejects(fn()=>$f['dep']->assertInstallable(),'installation prerequisite '.$case);
  check($f['apps']->disabled===[],'assertInstallable never changes another app '.$case);
  check($f['dep']->enforce()===$expected,'runtime fails closed '.$case);
  check($f['apps']->disabled===['passwords_otp'],'only OTP persistently disabled '.$case);
  $f['dep']->enforce();check($f['apps']->disabled===['passwords_otp'],'repeated dependency check is idempotent '.$case);
  check(!str_contains(json_encode($f['logger']->messages),'PRIVATE'),'logs contain only stable reason '.$case);
 }
 $f=fixture();$f['apps']->enabled['passwords']=false;$f['apps']->disableFails=true;
 check($f['dep']->enforce()==='passwords-disabled','configuration write failure still fails closed');
 check($f['logger']->messages[0][0]==='error','self-disable failure logged');
 check(!str_contains(json_encode($f['logger']->messages),'PRIVATE'),'self-disable error has no exception details');

 $output=new class implements \OCP\Migration\IOutput {};
 $schemaCalls=0;$schema=static function()use(&$schemaCalls){++$schemaCalls;throw new \RuntimeException('Schema must not be accessed');};
 $f=fixture();unset($f['apps']->versions['passwords_otp']);$f['apps']->enabled['passwords_otp']=false;
 $migration=new Version010102Date20261119000000($f['dep']);
 check($migration->changeSchema($output,$schema,[])===null,'fresh supported install migration is a schema no-op');
 check($schemaCalls===0,'fresh install never accesses schema');
 $f['apps']->enabled['passwords']=false;
 rejects(fn()=>$migration->changeSchema($output,$schema,[]),'fresh missing dependency aborts schema-only migration');
 check($f['apps']->disabled===[],'fresh failure does not mutate existing apps');
 check(!isset($f['apps']->versions['passwords_otp']),'fresh failure creates no installed version');
 $f=fixture();$f['apps']->enabled['passwords']=false;
 $migration=new Version010102Date20261119000000($f['dep']);
 check($migration->changeSchema($output,$schema,[])===null,'existing incompatible install does not block server upgrade');
 check($f['apps']->disabled===['passwords_otp'],'existing incompatible install disabled during upgrade');
 check($schemaCalls===0,'upgrade never accesses schema');

 $f=fixture();$f['listener']->handle(new AppEnableEvent('passwords_otp'));
 check($f['apps']->disabled===[],'valid OTP enable accepted');
 check($f['jobs']->added===[[CheckPasswordsDependency::class,null]],'successful enable restores own fallback job');
 $f['listener']->handle(new AppEnableEvent('passwords_otp',['pilot']));
 check($f['apps']->disabled===[],'valid group-restricted OTP enable accepted');
 $f['apps']->enabled['passwords']=false;
 rejects(fn()=>$f['listener']->handle(new AppEnableEvent('passwords_otp')),'invalid OTP enable');
 check($f['apps']->disabled===['passwords_otp'],'post-enable write rolled back');
 check(count($f['jobs']->added)===2,'rejected enable never restores job');
 $f['apps']->enabled['passwords']=true;$f['listener']->handle(new AppEnableEvent('passwords'));
 check(!$f['apps']->enabled['passwords_otp'],'restored Passwords never auto-enables OTP');
 $f=fixture();$f['apps']->enabled['passwords']=false;
 $f['apps']->onDisable=function($id)use($f){$f['listener']->handle(new AppDisableEvent($id));};
 $f['listener']->handle(new AppDisableEvent('passwords'));
 check($f['apps']->disabled===['passwords_otp'],'Passwords disable cascades without recursive disable');
 foreach([new AppUpdateEvent('passwords'),new AppUpdateEvent('passwords_otp')] as $event){
  $f=fixture();$f['apps']->info['version']='2026.12.1';$f['apps']->versions['passwords']='2026.12.1';
  $f['listener']->handle($event);check($f['apps']->disabled===['passwords_otp'],'update checks supported dependency '.$event->getAppId());
  check($f['jobs']->removed===[[CheckPasswordsDependency::class,null]],'update removes a job re-added after invalid migration '.$event->getAppId());
 }
 $f=fixture();$f['apps']->enabled['passwords']=false;
 foreach([new AppEnableEvent('unrelated'),new AppDisableEvent('unrelated'),new AppUpdateEvent('unrelated'),new AppDisableEvent('passwords_otp'),new \OCP\EventDispatcher\Event()] as $event)$f['listener']->handle($event);
 check($f['apps']->disabled===[],'unrelated and own disable events ignored');
 $f=fixture();$f['listener']->handle(new AppEnableEvent('passwords',['pilot']));
 check($f['apps']->disabled===[],'Passwords group restriction alone does not disable globally');

 $registration=new class implements \OCP\AppFramework\Bootstrap\IRegistrationContext {
  public array $listeners=[];public function registerEventListener($event,$listener){$this->listeners[$event]=$listener;}
 };
 $application=new Application();$application->register($registration);
 check($registration->listeners===[AppDisableEvent::class=>PasswordsLifecycleListener::class,AppEnableEvent::class=>PasswordsLifecycleListener::class,AppUpdateEvent::class=>PasswordsLifecycleListener::class],'all three public lifecycle events registered');
 $f=fixture();unlink($f['path'].'/appinfo/info.xml');
 $boot=new class($f['dep']) implements \OCP\AppFramework\Bootstrap\IBootContext {
  public function __construct(private PasswordsDependency $dependency){}public function injectFn(callable $fn){return $fn($this->dependency);}
 };
 $application->boot($boot);check($f['apps']->disabled===['passwords_otp'],'boot detects eventless file removal');
 $f=fixture();unlink($f['path'].'/appinfo/info.xml');
 $time=new class implements \OCP\AppFramework\Utility\ITimeFactory {};
 $job=new CheckPasswordsDependency($time,$f['dep']);
 check($job->interval===300&&!$job->parallel,'fallback job interval and non-parallel setting');
 (new \ReflectionMethod($job,'run'))->invoke($job,null);
 check($f['apps']->disabled===['passwords_otp'],'cron detects eventless file removal');
 $jobs=new FakeJobs();
 (new RemoveDependencyJob($jobs))->run($output);
 check($jobs->removed===[[CheckPasswordsDependency::class,null]],'disable removes only own dependency job before rollback/removal');
 echo "PHP_DEPENDENCY_PASS assertions=$passed php=".PHP_VERSION." (framework doubles; not live Nextcloud)\n";
}
