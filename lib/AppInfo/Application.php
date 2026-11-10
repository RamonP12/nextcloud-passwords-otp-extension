<?php

declare(strict_types=1);
namespace OCA\PasswordsOtp\AppInfo;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
final class Application extends App implements IBootstrap {
    public const APP_ID = 'passwords_otp';
    public function __construct(array $urlParams = []) { parent::__construct(self::APP_ID, $urlParams); }
    public function register(IRegistrationContext $context): void { /* Standard Nextcloud dependency injection. */ }
    public function boot(IBootContext $context): void { /* No global hooks or upstream changes. */ }
}
