<?php
// Framework doubles. The real Nextcloud core-component and live checks are separate.
declare(strict_types=1);

namespace OCP\App {
    class AppPathNotFoundException extends \RuntimeException {}
    interface IAppManager {
        public function getAppInstalledVersions();
        public function getAppPath($id, $ignoreCache = false);
        public function isEnabledForAnyone($id);
    }
}
namespace OCP\AppFramework { class App { public function __construct(...$args) {} } }
namespace OCP\BackgroundJob {
    interface IJobList { public function remove($class, $argument = null); }
    abstract class Job {
        public function start(IJobList $jobs): void {}
        abstract protected function run($argument);
    }
}
namespace OCP\Migration {
    interface IOutput {}
    interface IRepairStep { public function getName(); public function run(IOutput $output); }
    abstract class SimpleMigrationStep {}
}
namespace {
    require __DIR__.'/../../lib/AppInfo/Application.php';
    require __DIR__.'/../../lib/Service/PasswordsDependency.php';
    require __DIR__.'/../../lib/BackgroundJob/CheckPasswordsDependency.php';
    require __DIR__.'/../../lib/Migration/Version010102Date20261119000000.php';
    require __DIR__.'/../../lib/Migration/RemoveDependencyJob.php';

    use OCA\PasswordsOtp\BackgroundJob\CheckPasswordsDependency;
    use OCA\PasswordsOtp\Migration\RemoveDependencyJob;
    use OCA\PasswordsOtp\Migration\Version010102Date20261119000000;
    use OCA\PasswordsOtp\Service\PasswordsDependency;

    final class FakeApps implements \OCP\App\IAppManager {
        public array $versions = ['passwords' => '2026.11.20', 'passwords_otp' => '1.1.4'];
        public bool $enabled = true;
        public bool $missingPath = false;
        public bool $unavailable = false;
        public array $pathCalls = [];

        public function __construct(public string $path) {}
        public function getAppInstalledVersions() {
            if ($this->unavailable) throw new \RuntimeException('Private fixture error');
            return $this->versions;
        }
        public function getAppPath($id, $ignoreCache = false) {
            $this->pathCalls[] = [$id, $ignoreCache];
            if ($this->missingPath) throw new \OCP\App\AppPathNotFoundException('Private fixture path');
            return $this->path;
        }
        public function diskVersion(string $version): void {
            file_put_contents($this->path.'/appinfo/info.xml', '<info><id>passwords</id><version>'
                .htmlspecialchars($version, ENT_XML1).'</version></info>');
        }
        public function isEnabledForAnyone($id) { return $this->enabled; }
    }
    final class EnvironmentDouble {
        public function getUserId() {}
        public function isImpersonating() {}
    }
    final class TokenDouble { public function getWebUiToken() {} }
    final class IncompatibleTokenDouble { public function getWebUiToken($requiredNewArgument) {} }

    $passed = 0;
    function check(bool $value, string $label): void {
        global $passed;
        if (!$value) throw new \RuntimeException('FAIL: '.$label);
        ++$passed;
    }
    function reject(callable $run, string $reason): void {
        try { $run(); }
        catch (\RuntimeException $error) {
            check(str_contains($error->getMessage(), 'Passwords OTP cannot be enabled.')
                && str_contains($error->getMessage(), $reason), 'fresh install rejects '.$reason);
            return;
        }
        throw new \RuntimeException('Expected rejection '.$reason);
    }

    $path = sys_get_temp_dir().'/passwords-otp-dependency-'.bin2hex(random_bytes(8));
    mkdir($path.'/appinfo', 0700, true);
    $manifest = $path.'/appinfo/info.xml';
    register_shutdown_function(static function () use ($manifest, $path): void {
        @unlink($manifest);
        @rmdir($path.'/appinfo');
        @rmdir($path);
    });
    $apiClass = 'OCA\\Passwords\\Helper\\Token\\ApiTokenHelper';
    $apps = new FakeApps($path);
    $apps->diskVersion('2026.11.20');
    $dependency = new PasswordsDependency($apps);
    check($dependency->reason() === 'passwords-api-incompatible', 'missing upstream classes denied');
    class_alias(EnvironmentDouble::class, 'OCA\\Passwords\\Services\\EnvironmentService');
    if (($argv[1] ?? '') === '--incompatible-api') {
        class_alias(IncompatibleTokenDouble::class, $apiClass);
        check($dependency->reason() === 'passwords-api-incompatible', 'new mandatory upstream argument denied');
        echo "PHP_INCOMPATIBLE_API_PASS assertions=$passed\n";
        exit;
    }
    class_alias(TokenDouble::class, $apiClass);

    foreach (['2026.11.20', '2026.11.21', '2026.11.29'] as $version) {
        $apps->versions['passwords'] = $version;
        $apps->diskVersion($version);
        check($dependency->reason() === null, 'compatible maintenance version '.$version);
    }
    check($apps->pathCalls[0] === ['passwords', true], 'metadata lookup bypasses stale app path cache');
    foreach (['2026.11.19', '2026.11.30', '2026.12.20', '2026.11.21-build1', '2026.11.20.0'] as $version) {
        $apps->versions['passwords'] = $version;
        $apps->diskVersion($version);
        check($dependency->reason() === 'passwords-incompatible', 'unreviewed version '.$version);
    }
    $apps->versions['passwords'] = '2026.11.20';
    $apps->diskVersion('2026.11.20');
    check($dependency->reason() === null, 'baseline metadata is available');
    $mtime = filemtime($manifest);
    $apps->diskVersion('2026.11.21');
    touch($manifest, $mtime);
    check($dependency->reason() === 'passwords-update-pending', 'version drift detected even with preserved mtime');
    $apps->diskVersion('2026.11.20');
    $apps->enabled = false;
    check($dependency->reason() === 'passwords-disabled', 'disabled prerequisite denied');
    $migration = new Version010102Date20261119000000($dependency);
    $output = new class implements \OCP\Migration\IOutput {};
    $noSchema = static function (): void { throw new \RuntimeException('Unexpected schema change'); };
    check($migration->changeSchema($output, $noSchema, []) === null, 'existing app upgrade proceeds');
    unset($apps->versions['passwords_otp']);
    reject(fn() => $migration->changeSchema($output, $noSchema, []), 'passwords-disabled');
    $apps->enabled = true;
    check($migration->changeSchema($output, $noSchema, []) === null, 'valid fresh install proceeds without schema');
    $apps->missingPath = true;
    check($dependency->reason() === 'passwords-missing', 'missing path denied');
    $apps->missingPath = false;
    $apps->unavailable = true;
    check($dependency->reason() === 'passwords-unavailable', 'lookup failures denied');
    $apps->unavailable = false;
    unlink($manifest);
    check($dependency->reason() === 'passwords-missing', 'missing files denied');

    $jobs = new class implements \OCP\BackgroundJob\IJobList {
        public array $removed = [];
        public function remove($class, $argument = null) { $this->removed[] = $class; }
    };
    (new CheckPasswordsDependency())->start($jobs);
    (new RemoveDependencyJob($jobs))->run($output);
    check($jobs->removed === [CheckPasswordsDependency::class, CheckPasswordsDependency::class],
        'legacy scheduler entry is removed on its next run or normal disable');
    echo "PHP_DEPENDENCY_PASS assertions=$passed php=".PHP_VERSION." (framework doubles)\n";
}
