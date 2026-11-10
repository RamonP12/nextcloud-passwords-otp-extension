<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\Service;
use OCA\Passwords\Helper\Token\ApiTokenHelper;
use OCA\Passwords\Services\EnvironmentService;
use OCP\App\IAppManager;
use OCP\IUserSession;
use OCP\Server;
use Throwable;
/** Internal upstream helper, deliberately isolated; no privileged fallback or direct SQL. */
final class PasswordsAuthAdapter {
    public function __construct(private IAppManager $appManager, private IUserSession $userSession) {}
    public function currentValidUid(): ?string {
        try {
            $user = $this->userSession->getUser();
            if ($user === null || !$this->appManager->isEnabledForUser('passwords', $user)) return null;
            $environment = Server::get(EnvironmentService::class);
            if (!($environment instanceof EnvironmentService) || $environment->isImpersonating()
                    || $environment->getUserId() !== $user->getUID()) return null;
            return $user->getUID();
        } catch (Throwable) { return null; }
    }
    public function acquire(): array {
        try {
            $user = $this->userSession->getUser();
            if ($user === null) return ['status' => 'unavailable', 'reason' => 'login-required'];
            if (!$this->appManager->isEnabledForUser('passwords', $user)) {
                return ['status' => 'unavailable', 'reason' => 'passwords-disabled'];
            }
            $environment = Server::get(EnvironmentService::class);
            if (!($environment instanceof EnvironmentService)) return ['status' => 'unavailable', 'reason' => 'integration-unavailable'];
            if ($environment->isImpersonating()) return ['status' => 'unavailable', 'reason' => 'impersonation-denied'];
            if ($environment->getUserId() !== $user->getUID()) return ['status' => 'unavailable', 'reason' => 'user-context-mismatch'];
            $helper = Server::get(ApiTokenHelper::class);
            if (!($helper instanceof ApiTokenHelper)) return ['status' => 'unavailable', 'reason' => 'integration-unavailable'];
            [$token, $login] = $helper->getWebUiToken();
            if (!is_string($token) || $token === '' || !is_string($login) || $login === '') {
                return ['status' => 'unavailable', 'reason' => 'empty-api-token'];
            }
            return ['status' => 'ready', 'login' => $login, 'token' => $token];
        } catch (Throwable) { return ['status' => 'unavailable', 'reason' => 'integration-error']; }
    }
}
