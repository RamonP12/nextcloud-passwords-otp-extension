<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Service;

use OCA\PasswordsOtp\AppInfo\Application;
use OCP\App\AppPathNotFoundException;
use OCP\App\IAppManager;
use Psr\Log\LoggerInterface;
use RuntimeException;
use Throwable;

/** Global prerequisite only. User/group permissions remain a separate check. */
final class PasswordsDependency {
    public const APP_ID = 'passwords';
    // The upstream PHP integration is private: widen only after compatibility testing.
    public const SUPPORTED_VERSIONS = ['2026.11.20'];

    public function __construct(private IAppManager $appManager, private LoggerInterface $logger) {}

    /** A stable, non-sensitive reason, or null when the prerequisite is satisfied. */
    public function reason(): ?string {
        try {
            $installed = $this->appManager->getAppInstalledVersions()[self::APP_ID] ?? '';
            if ($installed === '') return 'passwords-missing';
            // Bypass the app-path cache to detect removal without an AppDisableEvent.
            $path = $this->appManager->getAppPath(self::APP_ID, true) . '/appinfo/info.xml';
            if (!is_file($path) || !is_readable($path)) return 'passwords-missing';
            $info = $this->appManager->getAppInfoByPath($path);
            if ($info === null || ($info['id'] ?? '') !== self::APP_ID) return 'passwords-missing';
            if (!$this->appManager->isEnabledForAnyone(self::APP_ID)) return 'passwords-disabled';
            $onDisk = $info['version'] ?? '';
            if ($onDisk !== $installed) return 'passwords-update-pending';
            if (!in_array($installed, self::SUPPORTED_VERSIONS, true)) return 'passwords-incompatible';
            return null;
        } catch (AppPathNotFoundException) {
            return 'passwords-missing';
        } catch (Throwable) {
            return 'passwords-unavailable';
        }
    }

    public function assertInstallable(): void {
        $reason = $this->reason();
        if ($reason !== null) throw new RuntimeException(self::message($reason));
    }

    /**
     * Persistent self-disable, also used after missed lifecycle events.
     * Failure to write config does not grant access: callers still receive the reason.
     */
    public function enforce(): ?string {
        $reason = $this->reason();
        if ($reason === null) return null;
        try {
            if ($this->appManager->isEnabledForAnyone(Application::APP_ID)) {
                // No automatic re-enable when Passwords returns; the admin decides.
                $this->appManager->disableApp(Application::APP_ID);
                $this->logger->warning('Passwords OTP disabled: {reason}', [
                    'app' => Application::APP_ID, 'reason' => $reason,
                ]);
            }
        } catch (Throwable) {
            $this->logger->error('Passwords OTP dependency unavailable; disabling the app failed.', [
                'app' => Application::APP_ID, 'reason' => $reason,
            ]);
        }
        return $reason;
    }

    /**
     * A new installation fails before installed_version is registered. An upgrade
     * of an existing app disables it instead, so it cannot block a server upgrade.
     */
    public function checkInstallation(): void {
        $versions = $this->appManager->getAppInstalledVersions();
        if (($versions[Application::APP_ID] ?? '') === '') {
            $this->assertInstallable();
        } else {
            $this->enforce();
        }
    }

    public static function message(string $reason): string {
        $detail = match ($reason) {
            'passwords-missing' => 'The Passwords app is not installed or its files are missing.',
            'passwords-disabled' => 'The Passwords app is disabled.',
            'passwords-update-pending' => 'The Passwords app version on disk does not match its installed version. Complete its update first.',
            'passwords-incompatible' => 'The installed Passwords app version has not been validated for this OTP release.',
            default => 'The Passwords app prerequisite could not be verified.',
        };
        return 'Passwords OTP cannot be enabled. ' . $detail
            . ' Install and enable Passwords ' . implode(' or ', self::SUPPORTED_VERSIONS)
            . ' before enabling Passwords OTP.';
    }
}
