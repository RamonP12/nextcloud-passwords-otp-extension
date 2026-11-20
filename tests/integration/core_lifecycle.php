<?php
declare(strict_types=1);
/**
 * Nextcloud 35.0.2 core-component integration, NOT a running Nextcloud server.
 * Loads pinned, unmodified AppManager, Installer, MigrationService, Repair,
 * CLI commands and public event/migration classes. Framework services, database
 * persistence, metadata parsing and upstream Passwords types are controlled doubles.
 */
namespace Psr\EventDispatcher { interface StoppableEventInterface { public function isPropagationStopped(): bool; } }
namespace Psr\Log { interface LoggerInterface {} }
namespace Psr\Clock { interface ClockInterface {public function now():\DateTimeImmutable;} }
namespace Psr\Container { interface ContainerInterface { public function get(string $id); } interface NotFoundExceptionInterface extends \Throwable {} interface ContainerExceptionInterface extends \Throwable {} }
namespace OCP {
 interface IConfig {} interface IAppConfig { public const VALUE_STRING=2; }
 interface IUser { public function getUID(); } interface IUserSession {} interface IGroup { public function getGID(); } interface IGroupManager {} interface ICacheFactory {}
 interface ITempManager {} class ServerVersion {}
 class Server { public static array $services=[]; public static function get(string $id) { return self::$services[$id] ?? throw new \RuntimeException('Missing test service: '.$id); } }
 class Util { public static function getVersion(): array {return [35,0,2,2];} }
 class Files { public static function rmdirr(string $path):void { \Harness\State::$manager->present[basename($path)]=false; } }
}
namespace OCA\Passwords\Helper\Token {class ApiTokenHelper {public function getWebUiToken() {}}}
namespace OCA\Passwords\Services {class EnvironmentService {public function getUserId() {}public function isImpersonating() {}}}
namespace OCP\DB { interface ISchemaWrapper {} }
namespace OCP\EventDispatcher { interface IEventDispatcher {} }
namespace OCP\BackgroundJob { interface IJobList {} }
namespace OCP\Http\Client { interface IClientService {} }
namespace OCP\L10N { interface IFactory {} }
namespace OCP\AppFramework { class App {public function __construct(...$args){}} }
namespace OCP\AppFramework\Bootstrap { interface IBootstrap {} interface IRegistrationContext {} interface IBootContext {} }
namespace Symfony\Component\Console\Input {interface InputInterface {public function getArgument($name);public function getOption($name);} }
namespace Symfony\Component\Console\Output {interface OutputInterface {public function writeln($text);} }
namespace Symfony\Component\Console\Command {
 class Command {
  public const FAILURE=1; public const SUCCESS=0;
  public function __construct() {}
  protected function configure():void {}
  protected function execute(\Symfony\Component\Console\Input\InputInterface $input, \Symfony\Component\Console\Output\OutputInterface $output):int {return 0;}
 }
}
namespace Stecman\Component\Symfony\Console\BashCompletion\Completion {
 interface CompletionAwareInterface {public function completeOptionValues($optionName, \Stecman\Component\Symfony\Console\BashCompletion\CompletionContext $context):array;public function completeArgumentValues($argumentName, \Stecman\Component\Symfony\Console\BashCompletion\CompletionContext $context):array;}
}
namespace Stecman\Component\Symfony\Console\BashCompletion {class CompletionContext {public function getCurrentWord():string{return '';}}}
namespace OC {
 class AppConfig {
  public array $values=[];
  public function setValue($app,$key,$value):void {$this->values[$app][$key]=$value;}
  public function getValue($app,$key,$default=''){return $this->values[$app][$key]??$default;}
  public function searchValues($key,...$args):array {$out=[];foreach($this->values as $app=>$values)if(isset($values[$key]))$out[$app]=$values[$key];return $out;}
  public function getAppInstalledVersions(bool $onlyEnabled=false):array {return $this->searchValues('installed_version');}
 }
}
namespace OC\Config {class ConfigManager {public function migrateConfigLexiconKeys($app):void {}public function updateLexiconEntries($app):void {}}}
namespace OC\App {
 class DependencyAnalyzer {public function analyze(array $info,bool $ignoreMax=false):array {return [];}}
 class InfoParser {public function parse(string $path):array {return \Harness\State::$manager->getAppInfo('passwords_otp');}}
}
namespace OC\App\AppStore\Fetcher {class AppFetcher {}}
namespace OC\AppFramework\Bootstrap {
 class Coordinator {
  public function runLazyRegistration(string $appId):void {}
 }
}
namespace OC\DB {
 class Connection {
  public array $migrations=[];
  public function tableExists(string $table):bool {return true;}
  public function getPrefix():string {return 'oc_';}
  public function getQueryBuilder():object {return new \Harness\Query($this);}
  public function insertIfNotExist($table,array $row):void {$this->migrations[$row['app']][]=$row['version'];}
 }
}
namespace Harness {
 const ROOT=__DIR__.'/../..';
 $source=getenv('OTP_NC_SOURCE');
 if(!$source) throw new \RuntimeException('Use nextcloud_lifecycle.py to verify pinned sources before execution');
 foreach([
  'lib/public/App/IAppManager.php','lib/public/App/AppPathNotFoundException.php',
  'lib/public/EventDispatcher/Event.php','lib/public/EventDispatcher/IEventListener.php',
  'lib/public/App/Events/AppEnableEvent.php','lib/public/App/Events/AppDisableEvent.php','lib/public/App/Events/AppUpdateEvent.php','lib/public/App/ManagerEvent.php',
  'lib/public/Migration/IOutput.php','lib/public/Migration/IRepairStep.php','lib/public/Migration/IMigrationStep.php','lib/public/Migration/SimpleMigrationStep.php',
  'lib/public/AppFramework/Utility/ITimeFactory.php','lib/public/BackgroundJob/IJob.php','lib/public/BackgroundJob/IParallelAwareJob.php','lib/public/BackgroundJob/Job.php','lib/public/BackgroundJob/TimedJob.php',
  'lib/private/Repair/Events/RepairErrorEvent.php','lib/private/Repair/Events/RepairInfoEvent.php','lib/private/Repair/Events/RepairStepEvent.php',
  'lib/private/Repair/Events/RepairWarningEvent.php','lib/private/Repair/Events/RepairAdvanceEvent.php','lib/private/Repair/Events/RepairFinishEvent.php','lib/private/Repair/Events/RepairStartEvent.php',
  'lib/private/EventDispatcher/ServiceEventListener.php','lib/private/App/AppManager.php','lib/private/Repair.php','lib/private/DB/MigrationService.php','lib/private/Installer.php',
  'core/Command/App/Enable.php','core/Command/App/Disable.php','core/Command/App/Remove.php','core/Command/App/Install.php',
 ] as $file) require $source.'/'.$file;
 spl_autoload_register(static function(string $class):void {
  $prefix='OCA\\PasswordsOtp\\';
  if(str_starts_with($class,$prefix)) {
   $file=ROOT.'/lib/'.str_replace('\\','/',substr($class,strlen($prefix))).'.php';
   if(is_file($file)) require $file;
  }
 });
 final class State {public static AppManager $manager;public static Dispatcher $dispatcher;public static array $cases=[];}
 final class Log implements \Psr\Log\LoggerInterface {public array $entries=[];public function __call($method,$args){$this->entries[]=[$method,$args[0]??''];}}
 final class Config implements \OCP\IConfig {
  public function __construct(public \OC\AppConfig $store){}
  public function getSystemValueBool($key,$default=false):bool {return $key==='installed';}
  public function getSystemValue($key,$default=null){return $default;}
  public function getAppValue($app,$key,$default=''){return $this->store->getValue($app,$key,$default);}
  public function setAppValue($app,$key,$value):void {$this->store->setValue($app,$key,$value);}
 }
 final class User implements \OCP\IUser {public function __construct(public string $id,public array $groups){}public function getUID(){return $this->id;}}
 final class Users implements \OCP\IUserSession {public ?User $user=null;public function getUser(){return $this->user;}}
 final class Groups implements \OCP\IGroupManager {public function getUserGroupIds($user):array {return $user->groups;}public function get($id){return new class($id) implements \OCP\IGroup {public function __construct(private $id){}public function getGID(){return $this->id;}public function getDisplayName(){return $this->id;}};}}
 final class Cache implements \OCP\ICacheFactory {}
 final class Container implements \Psr\Container\ContainerInterface {public function get(string $id){return \OCP\Server::get($id);}}
 final class Dispatcher implements \OCP\EventDispatcher\IEventDispatcher {
  public array $listeners=[];public array $events=[];
  public function dispatchTyped(\OCP\EventDispatcher\Event $event):void {$this->events[]=get_class($event);foreach($this->listeners[get_class($event)]??[] as $listener)$listener($event);}
  public function dispatch($name,$event):void {}
 }
 class Output implements \OCP\Migration\IOutput,\Symfony\Component\Console\Output\OutputInterface {
  public function __construct(...$args){}
  public array $lines=[];
  public function debug(string $message):void {$this->lines[]=$message;}public function info($message){$this->lines[]=$message;}public function warning($message){$this->lines[]=$message;}
  public function startProgress($max=0){}public function advance($step=1,$description=''){}public function finishProgress(){}public function writeln($text){$this->lines[]=$text;}
 }
 class_alias(Output::class,'OC\\Migration\\SimpleOutput');
 final class Input implements \Symfony\Component\Console\Input\InputInterface {
  public function __construct(public array $arguments,public array $options=[]){}
  public function getArgument($name){return $this->arguments[$name]??null;}public function getOption($name){return $this->options[$name]??($name==='groups'?[]:false);}
 }
 final class Query {
  public function __construct(private \OC\DB\Connection $db){}
  public function __call($name,$args){return $this;}
  public function createNamedParameter($value){return $value;}
  public function executeQuery(){return new class($this->db->migrations['passwords_otp']??[]) {public function __construct(private array $rows){}public function fetchFirstColumn(){return $this->rows;}public function closeCursor(){}};}
 }
 final class L10n implements \OCP\L10N\IFactory {public function get($app){return new class {public function getLanguageCode(){return 'en';}public function t($message,$args=[]){return vsprintf($message,$args);}};}}
 final class Jobs implements \OCP\BackgroundJob\IJobList {
  public array $jobs=[];public function add($class):void {if(!in_array($class,$this->jobs,true))$this->jobs[]=$class;}public function remove($class):void {$this->jobs=array_values(array_diff($this->jobs,[$class]));}public function setLastRun($job):void {}public function setExecutionTime($job,$time):void {}
 }
 final class Time implements \OCP\AppFramework\Utility\ITimeFactory {
  public function getTime():int {return 1000;} public function getDateTime($time='now',?\DateTimeZone $timezone=null):\DateTime {return new \DateTime($time,$timezone);}
  public function getDateTimeImmutable($time='now',?\DateTimeZone $timezone=null):\DateTimeImmutable {return new \DateTimeImmutable($time,$timezone);}
  public function now():\DateTimeImmutable {return new \DateTimeImmutable('@1000');}
  public function withTimeZone(\DateTimeZone $timezone):static {return $this;}
  public function getTimeZone(?string $timezone=null):\DateTimeZone {return new \DateTimeZone($timezone??'UTC');}
 }
 final class Client implements \OCP\Http\Client\IClientService {} final class Temp implements \OCP\ITempManager {}
 final class AppManager extends \OC\App\AppManager {
  public array $present=['passwords'=>true,'passwords_otp'=>true];
  public array $versions=['passwords'=>'2026.11.20','passwords_otp'=>'1.2.0-dev'];
  public function __construct(public Config $state,public Users $users,public Dispatcher $events,Log $log) {parent::__construct($users,$state,new Groups(),new Cache(),$events,$log,new \OCP\ServerVersion(),new \OC\Config\ConfigManager(),new \OC\App\DependencyAnalyzer());}
  public function getAppPath(string $appId,bool $ignoreCache=false):string {if(!($this->present[$appId]??false))throw new \OCP\App\AppPathNotFoundException('Absent test app');return $appId==='passwords_otp'?ROOT:ROOT.'/.build/synthetic-passwords';}
  public function getAppInfo(string $appId,bool $path=false,$lang=null):?array {
   if(!($this->present[$appId]??false))return null;
   $info=['id'=>$appId,'name'=>$appId,'version'=>$this->versions[$appId],'types'=>[],'repair-steps'=>['install'=>[],'uninstall'=>[],'pre-migration'=>[],'post-migration'=>[],'live-migration'=>[]], 'background-jobs'=>[],'remote'=>[],'public'=>[],'dependencies'=>[]];
   if($appId==='passwords_otp') {
    $xml=(string)file_get_contents(ROOT.'/appinfo/info.xml');
    foreach(['install','uninstall','pre-migration','post-migration'] as $key)if(preg_match('~<'.$key.'>(.*?)</'.$key.'>~s',$xml,$match)){preg_match_all('~<step>(.*?)</step>~s',$match[1],$steps);$info['repair-steps'][$key]=$steps[1];}
    if(preg_match('~<background-jobs>(.*?)</background-jobs>~s',$xml,$match)){preg_match_all('~<job>(.*?)</job>~s',$match[1],$jobs);$info['background-jobs']=$jobs[1];}
   }
   return $info;
  }
  public function setDiskVersion(string $version):void {
   $this->versions['passwords']=$version;
   file_put_contents($this->getAppPath('passwords').'/appinfo/info.xml',
       '<info><id>passwords</id><version>'.htmlspecialchars($version,ENT_XML1).'</version></info>');
  }
  public function getAppInfoByPath(string $path,?string $lang=null):?array {return $this->getAppInfo(str_contains($path,'synthetic-passwords')?'passwords':'passwords_otp');}
  public function getAppNamespace(string $appId):string {return $appId==='passwords_otp'?'OCA\\PasswordsOtp':'OCA\\Passwords';}
  public function getAppVersion(string $appId,bool $useCache=true):string {return $this->versions[$appId]??'0';}
  public function getAlwaysEnabledApps(){return [];}
  public function isShipped($appId){return false;}
  public function registerAutoloading(string $app,string $path,bool $force=false):void {}
  public function loadApp(string $app):void {}
  public function isAppCompatible(string $serverVersion,array $appInfo,bool $ignoreMax=false):bool {return true;}
  public function setAppTypes(string $app,array $appData):void {}
 }
 final class Installer extends \OC\Installer {
  public function isDownloaded(string $appId):bool {return State::$manager->present[$appId]??false;}
  public function getInstallPath():?string {return ROOT.'/.build/lifecycle-no-real-files';}
 }
 function fixture(bool $installed=false):array {
  $store=new \OC\AppConfig();$config=new Config($store);$log=new Log();$users=new Users();$events=new Dispatcher();
  $metadata=ROOT.'/.build/synthetic-passwords/appinfo';
  if(!is_dir($metadata))mkdir($metadata,0700,true);
  file_put_contents($metadata.'/info.xml','<info><id>passwords</id><version>2026.11.20</version></info>');
  $store->values=['passwords'=>['enabled'=>'yes','installed_version'=>'2026.11.20'],'passwords_otp'=>['enabled'=>$installed?'yes':'no']];
  if($installed)$store->values['passwords_otp']['installed_version']='1.1.1';
  $manager=new AppManager($config,$users,$events,$log);State::$manager=$manager;State::$dispatcher=$events;
  $db=new \OC\DB\Connection();$jobs=new Jobs();$output=new Output();
  \OCP\Server::$services=[\OCP\App\IAppManager::class=>$manager,\OC\AppConfig::class=>$store,\OCP\IConfig::class=>$config,\Psr\Log\LoggerInterface::class=>$log,\OC\DB\Connection::class=>$db,\OCP\BackgroundJob\IJobList::class=>$jobs,\OC\AppFramework\Bootstrap\Coordinator::class=>new \OC\AppFramework\Bootstrap\Coordinator()];
  $dependency=new \OCA\PasswordsOtp\Service\PasswordsDependency($manager);
  \OCP\Server::$services[\OCA\PasswordsOtp\Service\PasswordsDependency::class]=$dependency;
  \OCP\Server::$services[\OCA\PasswordsOtp\Migration\RemoveDependencyJob::class]=new \OCA\PasswordsOtp\Migration\RemoveDependencyJob($jobs);
  foreach(glob(ROOT.'/lib/Migration/Version*.php') as $file){$class='OCA\\PasswordsOtp\\Migration\\'.basename($file,'.php');\OCP\Server::$services[$class]=new $class($dependency);}
  \OCP\Server::$services[\OC\Repair::class]=new \OC\Repair($events,$log);
  $installer=new Installer(new \OC\App\AppStore\Fetcher\AppFetcher(),new Client(),new Temp(),$log,$config,$manager,new L10n(),true);
  return compact('store','config','log','users','events','manager','db','jobs','output','dependency','installer');
 }
 function check(bool $condition,string $label):void {if(!$condition)throw new \RuntimeException('CORE_COMPONENT_FAIL: '.$label);}
 function casePass(string $name):void {State::$cases[]=$name;}
 function throws(callable $fn,string $label):void {try{$fn();}catch(\Exception $e){check(str_contains($e->getMessage(),'Passwords OTP cannot be enabled.'),'expected prerequisite error for '.$label);return;}throw new \RuntimeException('Expected exception: '.$label);}
 function install(array $f):void {$f['installer']->installApp('passwords_otp');}
 function invokeCommand($command,Input $input,Output $output):int {$method=new \ReflectionMethod($command,'execute');return $method->invoke($command,$input,$output);}

 // Negative control: the real repair runner absorbs normal exceptions.
 $f=fixture();$repair=new \OC\Repair($f['events'],$f['log']);
 $repair->setRepairSteps([new class implements \OCP\Migration\IRepairStep {public function getName(){return 'Synthetic throwing repair';}public function run(\OCP\Migration\IOutput $output){throw new \RuntimeException('expected');}}]);
 $repair->run();check(in_array(\OC\Repair\Events\RepairErrorEvent::class,$f['events']->events,true),'normal repair exception is reported and swallowed');casePass('negative-control-repair-exception-is-not-install-gate');

 foreach(['missing-files','missing-registration','disabled','incompatible','update-pending'] as $reason){
  $f=fixture();
  if($reason==='missing-files')$f['manager']->present['passwords']=false;
  if($reason==='missing-registration')unset($f['store']->values['passwords']['installed_version']);
  if($reason==='disabled')$f['store']->values['passwords']['enabled']='no';
  if($reason==='incompatible'){$f['manager']->setDiskVersion('2026.12.1');$f['store']->values['passwords']['installed_version']='2026.12.1';}
  if($reason==='update-pending')$f['store']->values['passwords']['installed_version']='2026.10.1';
  throws(fn()=>install($f),'fresh install '.$reason);
  check(!isset($f['store']->values['passwords_otp']['installed_version']),'fresh install does not record installed_version '.$reason);
  check($f['db']->migrations===[],'failed migration not marked executed '.$reason);
  check($f['jobs']->jobs===[],'no background jobs before failed migration '.$reason);
  check($f['manager']->present['passwords_otp'],'downloaded files may remain after rejection');
  casePass('fresh-schema-only-install-rejected-'.$reason);
 }
 $f=fixture();install($f);check($f['store']->values['passwords_otp']['installed_version']==='1.2.0-dev','valid install records version');check(count($f['db']->migrations['passwords_otp'])===1,'valid migration recorded');$f['manager']->enableApp('passwords_otp');check($f['manager']->isEnabledForAnyone('passwords_otp'),'valid install enabled');casePass('valid-fresh-install-and-enable');


 foreach(['all-users','group'] as $scope){
  $f=fixture(true);
  if($scope==='group')$f['manager']->enableAppForGroups('passwords_otp',['pilot']);
  $saved=$f['store']->values['passwords_otp']['enabled'];
  $f['manager']->disableApp('passwords');
  check($f['dependency']->reason()==='passwords-disabled','runtime detects disabled Passwords');
  check($f['store']->values['passwords_otp']['enabled']===$saved,'OTP activation scope is preserved');
  $f['manager']->enableApp('passwords');
  check($f['dependency']->reason()===null && $f['store']->values['passwords_otp']['enabled']===$saved,'scope recovers without another activation');
  casePass('disable-and-restore-preserve-'.$scope);
 }
 $f=fixture(true);$f['manager']->disableApp('passwords_otp');
 $f['manager']->disableApp('passwords');$f['manager']->enableApp('passwords');
 check(!$f['manager']->isEnabledForAnyone('passwords_otp'),'operator-disabled OTP stays disabled');
 casePass('manual-otp-disable-is-respected');

 $f=fixture(true);$f['manager']->getEnabledApps();$f['manager']->enableAppForGroups('passwords',['pilot']);
 $f['users']->user=new User('outsider',[]);
 check(!$f['manager']->isEnabledForUser('passwords',$f['users']->user),'outsider denied');
 check($f['dependency']->reason()===null,'group restriction not global dependency failure');
 $f['users']->user=new User('member',['pilot']);
 check($f['manager']->isEnabledForUser('passwords',$f['users']->user),'member retains Passwords');
 casePass('group-restriction-preserves-global-availability');

 foreach([false,true] as $keepData){
  $f=fixture(true);$cmd=new \OC\Core\Command\App\Remove($f['manager'],$f['installer'],$f['log']);
  $code=invokeCommand($cmd,new Input(['app-id'=>'passwords'],['keep-data'=>$keepData]),$f['output']);
  check($code===0&&!$f['manager']->present['passwords'],'core remove path removes Passwords');
  check($f['dependency']->reason()==='passwords-missing','removed files cause runtime denial');
  check($f['manager']->isEnabledForAnyone('passwords_otp'),'removal leaves OTP activation intact');
  casePass($keepData?'core-remove-keep-data-denied-at-runtime':'core-remove-default-denied-at-runtime');
 }

 foreach([false,true] as $valid){
  $f=fixture(true);if(!$valid)$f['manager']->disableApp('passwords');
  check($f['manager']->upgradeApp('passwords_otp'),'core upgrade returns success');
  check($f['store']->values['passwords_otp']['installed_version']==='1.2.0-dev','core upgrade records version');
  check($f['manager']->isEnabledForAnyone('passwords_otp'),'core upgrade preserves existing enablement');
  check(($f['dependency']->reason()===null)===$valid,'upgrade preserves the runtime gate');
  check($f['jobs']->jobs===[],'upgrade does not schedule old job');
  casePass($valid?'core-otp-upgrade-compatible':'core-otp-upgrade-unavailable');
 }

 $f=fixture(true);$f['manager']->setDiskVersion('2026.11.21');
 check($f['dependency']->reason()==='passwords-update-pending','files/config mismatch is unavailable');
 check($f['manager']->upgradeApp('passwords'),'Passwords maintenance upgrade completes');
 check($f['dependency']->reason()===null,'matching maintenance version restores access');
 $f['manager']->setDiskVersion('2026.12.20');
 check($f['manager']->upgradeApp('passwords'),'out-of-range upgrade completes');
 check($f['dependency']->reason()==='passwords-incompatible','out-of-range package remains blocked');
 check($f['manager']->isEnabledForAnyone('passwords_otp'),'update leaves OTP activated');
 casePass('maintenance-update-permitted-new-release-line-denied');

 $f=fixture(true);
 $job=\OCA\PasswordsOtp\BackgroundJob\CheckPasswordsDependency::class;
 $f['jobs']->add($job);
 (new $job(new Time()))->start($f['jobs']);
 check($f['jobs']->jobs===[],'old job removes its persisted entry');
 check($f['manager']->isEnabledForAnyone('passwords_otp'),'cleanup never disables OTP');
 casePass('legacy-job-retired');

 $f=fixture();install($f);unset($f['store']->values['passwords_otp']['installed_version']);
 $f['manager']->present['passwords']=false;install($f);$f['manager']->enableApp('passwords_otp');
 check($f['dependency']->reason()==='passwords-missing','runtime blocks reinstall with retained migration history');
 casePass('retained-migration-history-still-requires-runtime-guard');

 foreach([false,true] as $valid){
  $f=fixture();if(!$valid)$f['manager']->disableApp('passwords');
  $cmd=new \OC\Core\Command\App\Enable($f['manager'],new Groups(),$f['installer']);
  $code=invokeCommand($cmd,new Input(['app-id'=>['passwords_otp']]),$f['output']);
  check($code===($valid?0:1),'CLI first-registration result matches prerequisite');
  check($f['manager']->isEnabledForAnyone('passwords_otp')===$valid,'CLI enables fresh compatible app');
  casePass($valid?'real-occ-enable-fresh-valid':'real-occ-enable-fresh-unavailable');
 }

 echo json_encode(['status'=>'CORE_COMPONENT_PASS','scope'=>'Unmodified Nextcloud 35.0.2 core classes with controlled framework, metadata, Passwords and database doubles; not a live Nextcloud installation','php'=>PHP_VERSION,'cases'=>State::$cases,'limitations'=>['No real database, DI container or HTTP middleware','No real Passwords backend or certificate','No live browser/Nextcloud acceptance','Uses controllable Passwords class doubles']],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n";
}
