<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Service;

use OCA\Passwords\Helper\Token\ApiTokenHelper;
use OCA\Passwords\Services\EnvironmentService;
use OCA\PasswordsOtp\AppInfo\Application;
use OCP\App\AppPathNotFoundException;
use OCP\App\IAppManager;
use ReflectionException;
use ReflectionMethod;
use RuntimeException;
use Throwable;

/** Global prerequisite only. User/group permissions remain a separate check. */
final class PasswordsDependency {
    public const APP_ID = 'passwords';
    // The installer checks use this exact build. Runtime also accepts stable patch
    // builds in this release line, subject to the metadata and interface checks.
    public const REVIEWED_VERSION = '2026.11.20';
    private const REQUIRED_METHODS = [
        ApiTokenHelper::class => ['getWebUiToken'],
        EnvironmentService::class => ['getUserId', 'isImpersonating'],
    ];

    public function __construct(private IAppManager $appManager) {}

    /** A stable, non-sensitive reason, or null when the prerequisite is satisfied. */
    public function reason(): ?string {
        try {
            $installed = $this->appManager->getAppInstalledVersions()[self::APP_ID] ?? '';
            if ($installed === '') return 'passwords-missing';
            $path = $this->appManager->getAppPath(self::APP_ID, true) . '/appinfo/info.xml';
            clearstatcache(true, $path);
            if (!is_file($path) || !is_readable($path)) return 'passwords-missing';
            // Core caches info.xml by mtime, which may be preserved by an update.
            $xml = @file_get_contents($path);
            if ($xml === false) return 'passwords-missing';
            $info = @simplexml_load_string($xml, \SimpleXMLElement::class, LIBXML_NONET);
            if ($info === false || (string) $info->id !== self::APP_ID) return 'passwords-missing';
            if (!$this->appManager->isEnabledForAnyone(self::APP_ID)) return 'passwords-disabled';
            if ((string) $info->version !== $installed) return 'passwords-update-pending';
            $releaseLine = substr(self::REVIEWED_VERSION, 0, -1);
            if (strlen($installed) !== strlen(self::REVIEWED_VERSION)
                    || !str_starts_with($installed, $releaseLine)
                    || !ctype_digit(substr($installed, -1))) return 'passwords-incompatible';
            foreach (self::REQUIRED_METHODS as $class => $methods) {
                foreach ($methods as $name) {
                    $method = new ReflectionMethod($class, $name);
                    if (!$method->isPublic() || $method->isStatic() || $method->isAbstract()
                            || $method->getNumberOfRequiredParameters() !== 0) return 'passwords-api-incompatible';
                }
            }
            return null;
        } catch (AppPathNotFoundException) {
            return 'passwords-missing';
        } catch (ReflectionException) {
            return 'passwords-api-incompatible';
        } catch (Throwable) {
            return 'passwords-unavailable';
        }
    }

    /** A new installation can fail before its installed_version is registered. */
    public function checkInstallation(): void {
        $versions = $this->appManager->getAppInstalledVersions();
        if (($versions[Application::APP_ID] ?? '') !== '') return;
        $reason = $this->reason();
        if ($reason !== null) {
            $latestPatch = substr(self::REVIEWED_VERSION, 0, -1) . '9';
            throw new RuntimeException('Passwords OTP cannot be enabled. Install and enable a compatible Passwords '
                . self::REVIEWED_VERSION . '–' . $latestPatch
                . ' build and complete any pending updates. Reason: ' . $reason);
        }
    }
}
