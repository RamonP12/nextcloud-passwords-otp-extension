<?php
// Framework contract doubles. This does not replace a real Nextcloud middleware test.
declare(strict_types=1);
namespace OCP {
 interface IRequest {public function getServerProtocol();public function getHeader($name);}
 interface ISession {public function getId();}
 interface IURLGenerator {public function linkToRoute($name);}
 interface IUserSession {public function getUser();}
 class Server {public static array $services=[];public static function get($name){return self::$services[$name]??throw new \RuntimeException('PRIVATE');}}
 class Util {public static array $scripts=[];public static array $styles=[];public static function addScript($a,$b){self::$scripts[]=[$a,$b];}public static function addStyle($a,$b){self::$styles[]=[$a,$b];}}
}
namespace OCP\App {interface IAppManager {public function isEnabledForUser($id,$user);}}
namespace OCP\AppFramework {class Controller {public function __construct($app,protected $request){}} class App {public function __construct(...$x){}}}
namespace OCP\AppFramework\Bootstrap {interface IBootstrap{} interface IRegistrationContext{} interface IBootContext{}}
namespace OCP\AppFramework\Http\Attribute {
 #[\Attribute(\Attribute::TARGET_METHOD)] class NoAdminRequired{}
 #[\Attribute(\Attribute::TARGET_METHOD)] class NoCSRFRequired{}
 #[\Attribute(\Attribute::TARGET_METHOD)] class UseSession{}
}
namespace OCP\AppFramework\Http {
 class JSONResponse {public array $headers=[];public function __construct(public array $data,public int $status=200){}public function addHeader($key,$value){$this->headers[$key]=$value;}}
 class TemplateResponse {public array $headers=[];public object $policy;public function __construct(...$x){$this->policy=new class {public bool $wasm=false;public function allowEvalWasm($v){$this->wasm=$v;}};}public function getContentSecurityPolicy(){return $this->policy;}public function addHeader($key,$value){$this->headers[$key]=$value;}}
}
namespace OCP\AppFramework\Services {interface IInitialState {public function provideInitialState($key,$value);}}
namespace OCA\Passwords\Services {class EnvironmentService {public string $uid='synthetic';public bool $impersonating=false;public function isImpersonating(){return $this->impersonating;}public function getUserId(){return $this->uid;}}}
namespace OCA\Passwords\Helper\Token {class ApiTokenHelper {public int $calls=0;public mixed $callback=null;public array $value=['PRIVATE-TOKEN','synthetic'];public function getWebUiToken(){++$this->calls;if($this->callback)($this->callback)();return $this->value;}}}
namespace {
 require __DIR__.'/../../lib/AppInfo/Application.php';
 require __DIR__.'/../../lib/Service/PasswordsAuthAdapter.php';
 require __DIR__.'/../../lib/Controller/PageController.php';
 use OCA\PasswordsOtp\Service\PasswordsAuthAdapter;
 use OCA\PasswordsOtp\Controller\PageController;
 use OCA\Passwords\Services\EnvironmentService;
 use OCA\Passwords\Helper\Token\ApiTokenHelper;
 use OCP\Server;
 $passed=0;
 function check(bool $value,string $label):void {global $passed;if(!$value)throw new \RuntimeException('FAIL: '.$label);++$passed;}
 function fixture():array {
  $request=new class implements \OCP\IRequest {public string $protocol='https';public string $header='';public function getServerProtocol(){return $this->protocol;}public function getHeader($name){return $this->header;}};
  $session=new class implements \OCP\ISession {public string $id='synthetic-session';public function getId(){return $this->id;}};
  $users=new class implements \OCP\IUserSession {public bool $enabled=true;public function getUser(){return $this->enabled?new class {public function getUID(){return 'synthetic';}}:null;}};
  $apps=new class implements \OCP\App\IAppManager {public bool $enabled=true;public function isEnabledForUser($id,$user){return $id==='passwords'&&$this->enabled;}};
  $initial=new class implements \OCP\AppFramework\Services\IInitialState {public array $state=[];public function provideInitialState($key,$value){$this->state=$value;}};
  $urls=new class implements \OCP\IURLGenerator {public bool $fail=false;public function linkToRoute($name){if($this->fail)throw new \RuntimeException('PRIVATE');return '/synthetic/'.$name;}};
  $environment=new EnvironmentService();$helper=new ApiTokenHelper();
  Server::$services=[EnvironmentService::class=>$environment,ApiTokenHelper::class=>$helper];
  $adapter=new PasswordsAuthAdapter($apps,$users);
  $controller=new PageController($request,$initial,$urls,$adapter,$session);
  return compact('request','session','users','apps','initial','urls','environment','helper','adapter','controller');
 }
 $f=fixture();$response=$f['controller']->index();
 check($f['initial']->state['status']==='ready','authenticated initial state');
 check(!str_contains(json_encode($f['initial']->state),'PRIVATE'),'no token in HTML state');
 check($f['helper']->calls===0,'HTML must not acquire token');
 check($response->policy->wasm===true,'upstream WASM enabled');
 check($response->headers['Cache-Control']==='private, no-store, max-age=0','HTML no-store');
 $xml=(string)file_get_contents(__DIR__.'/../../appinfo/info.xml');
 $versionMatches=[];
 $hasVersion=preg_match('/<version>([0-9]+\.[0-9]+\.[0-9]+)<\/version>/', $xml, $versionMatches)===1;
 $expectedAsset=$hasVersion?'app-'.str_replace('.','',$versionMatches[1]):'';
 check($expectedAsset!==''&&\OCP\Util::$scripts[0][1]===$expectedAsset&&\OCP\Util::$styles[0][1]===$expectedAsset,'versioned assets match app metadata');
 $fingerprint=$f['initial']->state['sessionFingerprint'];
 $status=$f['controller']->sessionStatus();
 check($status->data===['authenticated'=>true,'sessionFingerprint'=>$fingerprint],'status same session');
 check($f['helper']->calls===0,'status must not acquire token');
 check($status->headers['X-Content-Type-Options']==='nosniff','JSON nosniff');
 foreach(['',str_repeat('b',64),'INVALID',$fingerprint.'\n'] as $bad){
  $f['request']->header=$bad;$res=$f['controller']->bootstrap();
  check($res->status===403,'reject wrong binding');check($f['helper']->calls===0,'binding before token acquisition');
 }
 $f['request']->header=$fingerprint;$res=$f['controller']->bootstrap();
 check($res->status===200&&$res->data['sessionFingerprint']===$fingerprint,'valid bootstrap binding');
 check($res->data['token']==='PRIVATE-TOKEN','token only in protected POST');
 check($res->headers['Cache-Control']==='private, no-store, max-age=0','bootstrap no-store');
 $f['helper']->callback=function()use($f){$f['session']->id='changed';};
 $res=$f['controller']->bootstrap();check($res->status===403&&!str_contains(json_encode($res->data),'PRIVATE'),'session change during acquisition');
 foreach(['users','apps','impersonating','uid','missing-environment','missing-helper','empty-token'] as $case){
  $f=fixture();
  if($case==='users'||$case==='apps')$f[$case]->enabled=false;
  elseif($case==='impersonating')$f['environment']->impersonating=true;
  elseif($case==='uid')$f['environment']->uid='other';
  elseif($case==='missing-environment')unset(Server::$services[EnvironmentService::class]);
  elseif($case==='missing-helper')unset(Server::$services[ApiTokenHelper::class]);
  else $f['helper']->value=['','synthetic'];
  $acquired=$f['adapter']->acquire();check($acquired['status']==='unavailable','adapter fails closed '.$case);
  check(!str_contains(json_encode($acquired),'PRIVATE'),'adapter sanitized '.$case);
 }
 $f=fixture();$f['request']->protocol='http';
 check($f['controller']->bootstrap()->status===403,'no HTTP bootstrap');
 check($f['controller']->sessionStatus()->status===403,'no HTTP status');
 $f['controller']->index();check($f['initial']->state['status']==='unavailable','no HTTP HTML credentials');
 check($f['helper']->calls===0,'HTTP never acquires token');
 $f=fixture();$f['session']->id='';check($f['controller']->sessionStatus()->status===403,'empty session refused');
 $f=fixture();$f['urls']->fail=true;$f['controller']->index();check($f['initial']->state['status']==='unavailable','route exception sanitized');
 $method=new \ReflectionMethod(PageController::class,'bootstrap');
 $attributes=array_map(fn($a)=>$a->getName(),$method->getAttributes());
 check(in_array(\OCP\AppFramework\Http\Attribute\UseSession::class,$attributes,true),'bootstrap session required');
 check(!in_array(\OCP\AppFramework\Http\Attribute\NoCSRFRequired::class,$attributes,true),'bootstrap CSRF middleware retained');
 foreach((new \ReflectionClass(PageController::class))->getMethods(\ReflectionMethod::IS_PUBLIC)as$m){
  foreach($m->getAttributes()as$a)check(!str_ends_with($a->getName(),'PublicPage'),'no public route');
 }
 echo "PHP_SECURITY_PASS assertions=$passed php=".PHP_VERSION." (framework doubles; not real Nextcloud)\n";
}
